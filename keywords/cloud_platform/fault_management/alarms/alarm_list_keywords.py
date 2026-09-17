import re
import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_output import AlarmListOutput


class AlarmListKeywords(BaseKeyword):
    """
    Class for alarm list keywords
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): Active SSH connection used for remote operations.
        """
        self._ssh_connection = ssh_connection
        self._check_interval_in_seconds = 3
        self._timeout_in_seconds = 600

    def get_alarm_list(self, uuid: bool = False) -> AlarmListOutput:
        """Keyword to get all alarms.

        Args:
            uuid (bool): If True, include UUID column in the output (--uuid flag).

        Returns:
            AlarmListOutput: List of alarm objects retrieved from the system.
        """
        uuid_flag = " --uuid" if uuid else ""
        output = self._ssh_connection.send(source_openrc(f"fm alarm-list --nowrap{uuid_flag}"))
        self.validate_success_return_code(self._ssh_connection)
        alarms_output = AlarmListOutput(output)

        return alarms_output

    def alarm_list(self) -> list[AlarmListObject]:
        """
        Get all alarms as a list.

        Returns:
            list[AlarmListObject]: List of alarm objects.
        """
        return self.get_alarm_list().get_alarms()

    def wait_for_all_alarms_cleared(self, dwell_seconds: int = 60, transient_alarm_ids: list[str] = None) -> None:
        """Wait for all alarms to be cleared and to stay cleared for a stable dwell window.

        A single empty 'fm alarm-list' sample is not treated as steady state. The alarm list must
        stay clear for at least 'dwell_seconds' since the first clear sample before this method
        returns. This debounces flapping alarms (e.g. a "Configuration is out-of-date" alarm that
        sets, clears, and re-sets while the platform re-applies config) that would otherwise let the
        check pass during a momentary clear window.

        Reuses validate_equals_with_retry() from framework.validation for the poll/timeout loop; the
        dwell tracking is a stateful predicate driven by that helper.

        Notes:
            The alarms in this SSH connection are checked every get_check_interval_in_seconds() seconds
            and the overall wait is bounded by get_timeout_in_seconds().

        Args:
            dwell_seconds (int): Minimum time in seconds the alarm list must stay clear before success
                is declared. Defaults to 60.
            transient_alarm_ids (list[str]): Optional allowlist of alarm IDs treated as still-reconciling
                rather than hard alarms. Alarms whose ID is in this list do not block or reset the dwell
                window. Defaults to none (every alarm is treated as blocking).

        Returns: None

        Raises:
            TimeoutError: if the alarms can not be cleared and remain clear for the dwell window within
                the period defined by the get_timeout_in_seconds() seconds.
        """
        # Delegate to the unified debounced implementation. 'transient_alarm_ids' are treated as
        # still-reconciling (excluded). The dwell window alone governs stability now.
        self.wait_for_all_alarms_cleared_excluding(
            excluded_alarm_ids=transient_alarm_ids if transient_alarm_ids is not None else [],
            dwell_seconds=dwell_seconds,
        )

    def wait_for_all_alarms_cleared_excluding(self, excluded_alarm_ids: list[str] = None, excluded_alarms: list[AlarmListObject] = None, stable_checks: int = 1, tolerate_query_failure: bool = False, dwell_seconds: int = 0) -> None:
        """Wait for all alarms to be cleared except the ones excluded, and to stay clear.

        This is the single debounced implementation used by wait_for_all_alarms_cleared(). Success
        requires the non-excluded alarm list to stay clear for at least an effective dwell window
        since the first clear sample. The effective dwell is derived from both 'dwell_seconds' and
        'stable_checks':

            effective_dwell = max(dwell_seconds, (stable_checks - 1) * get_check_interval_in_seconds())

        This maps the older "N consecutive clears at the poll interval" semantics onto an equivalent
        time window while tracking a single variable (the first clear time). Any reappearing alarm
        resets that clear time, so a momentary clear window during a flapping alarm does not satisfy
        the wait. Reuses validate_equals_with_retry() from framework.validation for the poll/timeout
        loop.

        Alarms can be excluded in two complementary ways:
        - 'excluded_alarm_ids': ignore any alarm whose alarm ID is in this list
          (e.g. ['900.007']). Matches on the alarm ID only.
        - 'excluded_alarms': ignore any alarm equal to one in this list. Equality
          uses the full alarm identity (alarm_id + severity + entity_id via
          AlarmListObject.__eq__). Pass a snapshot of the alarms that were already
          active before an operation so only alarms that appeared afterwards are
          waited on. This correctly still waits on a new alarm whose type already
          existed on a different entity or at a different severity.

        Notes:
            The alarms in this SSH connection are checked every get_check_interval_in_seconds() seconds
            and the overall wait is bounded by get_timeout_in_seconds().

        Args:
            excluded_alarm_ids (list[str]): Alarm IDs to ignore (e.g. ['900.007']). Defaults to none.
            excluded_alarms (list[AlarmListObject]): Full alarm objects to ignore, matched by
                alarm_id + severity + entity_id. Defaults to none.
            stable_checks (int): Number of clean polls' worth of dwell required before returning,
                expressed as time via (stable_checks - 1) * get_check_interval_in_seconds(). Defaults
                to 1 (no additional dwell from this parameter; return as soon as the alarms are first
                seen cleared unless dwell_seconds requires longer). Use a higher value to absorb
                flapping alarms that briefly re-raise while the platform is still recovering.
            tolerate_query_failure (bool): If True, an alarm query that fails (e.g. while Keystone is
                restarting and the platform is temporarily unavailable) is treated as "not ready yet" and
                retried instead of aborting the wait. Defaults to False (the exception propagates).
            dwell_seconds (int): Minimum time in seconds the alarm list must stay clear before success is
                declared. Defaults to 0 (pass on the first clear sample when stable_checks is also 1).

        Raises:
            TimeoutError: If non-excluded alarms are not cleared and stable within the timeout.
        """
        excluded_alarm_ids = excluded_alarm_ids if excluded_alarm_ids is not None else []
        excluded_alarms = excluded_alarms if excluded_alarms is not None else []
        check_interval = self.get_check_interval_in_seconds()
        # Collapse the old count-based stability gate into the single dwell window so only one
        # stability variable (first_clear_time) needs to be tracked. N consecutive clears at the
        # poll interval is equivalent to a (N - 1) * interval dwell.
        effective_dwell = max(dwell_seconds, (stable_checks - 1) * check_interval)

        # Stateful predicate driven by validate_equals_with_retry(). Returns True only once the
        # non-excluded alarm list has stayed clear for 'effective_dwell' seconds since the first
        # clear sample. Resets the clear time on any reappearing alarm.
        dwell_state = {"first_clear_time": None}

        def is_alarms_cleared_and_stable() -> bool:
            # During recovery the platform services (e.g. Keystone) may be briefly unavailable, making
            # 'fm alarm-list' fail. When tolerated, treat that as "not ready yet" and reset the timer.
            try:
                blocking_alarms = [alarm for alarm in self.alarm_list() if alarm.get_alarm_id() not in excluded_alarm_ids and alarm not in excluded_alarms]
            except Exception as alarm_query_error:
                if not tolerate_query_failure:
                    raise
                get_logger().log_info(f"Could not query alarms yet (platform may still be recovering): {alarm_query_error}. Retrying.")
                dwell_state["first_clear_time"] = None
                return False

            if not blocking_alarms:
                if dwell_state["first_clear_time"] is None:
                    dwell_state["first_clear_time"] = time.time()
                dwell_elapsed = time.time() - dwell_state["first_clear_time"]
                if dwell_elapsed >= effective_dwell:
                    get_logger().log_info(f"All alarms cleared (excluding {excluded_alarm_ids}) and stable.")
                    return True
                get_logger().log_info(f"Alarms clear (excluding {excluded_alarm_ids}), confirming stability: dwell {dwell_elapsed:.3f}/{effective_dwell} seconds.")
                return False

            alarm_ids = ", ".join([alarm.get_alarm_id() for alarm in blocking_alarms])
            if dwell_state["first_clear_time"] is not None:
                get_logger().log_info(f"Alarm(s) reappeared during the dwell window, resetting the dwell timer. Reappeared alarm IDs: {alarm_ids}.")
                dwell_state["first_clear_time"] = None
            get_logger().log_info(f"Active alarms (excluding {excluded_alarm_ids}): {alarm_ids}.")
            return False

        validate_equals_with_retry(
            is_alarms_cleared_and_stable,
            True,
            f"All alarms cleared (excluding {excluded_alarm_ids}) and stable for {effective_dwell}s in this SSH connection ({self.get_ssh_connection()})",
            timeout=self.get_timeout_in_seconds(),
            polling_sleep_time=check_interval,
        )

    def wait_for_alarms_cleared(self, alarms: list[AlarmListObject]) -> None:
        """
        Wait for alarms be cleared

        This method waits for the alarms defined in 'alarms' to be cleared in this SSH connection within the period
        defined by 'get_timeout_in_seconds()'. Otherwise, a TimeoutError exception is raised.

        Notes:
            The alarms in this SSH connection are checked every 'get_check_interval_in_seconds()' seconds.

        Args:
            alarms (list[AlarmListObject]): The list of alarms to be checked to see if they have been cleared
                in this SSH connection.

        Returns: None

        Raises:
            TimeoutError: if some alarm can not be cleared within a period defined by
                the `get_timeout_in_seconds()` seconds; False otherwise.
        """
        current_alarms = self.alarm_list()
        alarm_ids = ", ".join([alarm.get_alarm_id() for alarm in alarms])

        now = time.time()
        end_time = now + self.get_timeout_in_seconds()
        while now < end_time:
            alarms_are_cleared = True

            for alarm in alarms:
                # Note: AlarmListObject overrides __eq__ method and the operator 'in' uses this overridden method.
                if alarm in current_alarms:
                    get_logger().log_info(f"The alarm with ID {alarm.get_alarm_id()} is still active in this SSH connection ({self.get_ssh_connection()}).")
                    alarms_are_cleared = False

            if alarms_are_cleared:
                get_logger().log_info(f"All alarms defined by the following IDs: {alarm_ids} are now cleared in this SSH connection ({self.get_ssh_connection()}).")
                return

            get_logger().log_info(f"Not all alarms with the following IDs: {alarm_ids} have been cleared in this SSH connection ({self.get_ssh_connection()}). Waiting for {self.get_check_interval_in_seconds():.3f} more seconds. Remaining time: {(end_time - now):.3f} seconds.")
            time.sleep(self._check_interval_in_seconds)
            current_alarms = self.alarm_list()
            now = time.time()

        raise TimeoutError(f"The alarms identified by the following IDs: {alarm_ids} could not be cleared within a period of {self.get_timeout_in_seconds()} seconds.")

    def wait_for_alarms_to_appear(self, alarms: list[AlarmListObject]) -> list[AlarmListObject]:
        """
        Wait for an alarm to appear

        Waits for the specified alarms to appear on the SSH connection within the timeout
        period defined by 'get_timeout_in_seconds()'. Validates Alarm ID, Reason Text, and Entity ID.

        Args:
            alarms (list[AlarmListObject]): The list of alarms to wait for.

        Returns:
            list[AlarmListObject]: The matched observed alarms (with UUIDs populated).

        Raises:
            TimeoutError: if alarms are not found within the timeout period.
        """
        check_interval = self.get_check_interval_in_seconds()
        end_time = time.time() + self.get_timeout_in_seconds()

        alarm_descriptions = ", ".join(str(alarm) for alarm in alarms)
        while time.time() < end_time:
            alarm_output = self.get_alarm_list(uuid=True)
            observed_alarms = alarm_output.get_alarms()

            matched_alarms = []
            all_matched = True
            for expected_alarm_obj in alarms:
                match = None
                for observed_alarm_obj in observed_alarms:
                    if self.alarms_match(observed_alarm_obj, expected_alarm_obj):
                        match = observed_alarm_obj
                        break
                if match:
                    matched_alarms.append(match)
                else:
                    get_logger().log_info(f"Expected alarm not found yet: {expected_alarm_obj}")
                    all_matched = False
                    break

            if all_matched:
                get_logger().log_info(f"All expected alarms are now present: {alarm_descriptions}")
                return matched_alarms

            get_logger().log_info(f"Waiting for expected alarms. Retrying in {check_interval:.3f} seconds. Remaining time: {end_time - time.time():.3f} seconds.")
            time.sleep(check_interval)

        # Final check before raising
        alarm_output = self.get_alarm_list(uuid=True)
        observed_alarms = alarm_output.get_alarms()
        observed_alarm_str = [str(observed_alarm_obj) for observed_alarm_obj in observed_alarms]
        raise TimeoutError(f"Timeout. Alarms not found:\nExpected: {alarm_descriptions}\nObserved alarms:\n" + "\n".join(observed_alarm_str))

    def alarms_match(self, observed_alarm_object: AlarmListObject, expected_alarm_object: AlarmListObject) -> bool:
        """
        Compares two AlarmListObject instances for equality based on alarm ID, reason text, entity ID, and severity.

        Args:
            observed_alarm_object (AlarmListObject): The current alarm object to compare against.
            expected_alarm_object (AlarmListObject): The expected alarm object.

        Returns:
            bool: True if all fields (alarm ID, reason text, entity ID, and severity) match exactly
                (after stripping whitespace for text fields), False otherwise.
        """
        observed_id = observed_alarm_object.get_alarm_id()
        expected_id = expected_alarm_object.get_alarm_id()

        observed_reason_text = observed_alarm_object.get_reason_text()
        expected_reason_text_pattern = expected_alarm_object.get_reason_text()

        observed_entity_id = observed_alarm_object.get_entity_id()
        expected_entity_id = expected_alarm_object.get_entity_id()

        observed_severity = observed_alarm_object.get_severity()
        expected_severity = expected_alarm_object.get_severity()

        # Perform the comparisons, making each condition clear.
        id_matches = observed_id == expected_id
        if expected_reason_text_pattern is None:
            reason_text_matches = True
        elif isinstance(expected_reason_text_pattern, list):
            reason_text_matches = any(re.fullmatch(pattern, observed_reason_text) for pattern in expected_reason_text_pattern)
        else:
            reason_text_matches = re.fullmatch(expected_reason_text_pattern, observed_reason_text)
        entity_id_matches = expected_entity_id is None or observed_entity_id == expected_entity_id
        severity_matches = expected_severity is None or observed_severity == expected_severity

        # Return True only if all conditions are met.
        return id_matches and reason_text_matches and entity_id_matches and severity_matches

    def get_timeout_in_seconds(self) -> int:
        """
        Gets an integer representing the maximum time in seconds to wait for the alarms to be cleared, default value: 600.

        Returns:
            int: An integer representing the maximum time in seconds to wait for the alarms to be cleared.
        """
        return self._timeout_in_seconds

    def set_timeout_in_seconds(self, timeout_in_seconds: int):
        """
        Sets the integer representation of the maximum time in seconds to wait for the alarms to be cleared.

        Args:
            timeout_in_seconds (int): An integer representing the maximum time to wait for the alarms to be cleared.
        """
        self._timeout_in_seconds = timeout_in_seconds

    def get_check_interval_in_seconds(self) -> int:
        """
        Gets an integer representing the interval in seconds at which this instance will check the alarms again, default value: 3.

        Returns:
            int: An integer representing the interval in seconds at which this instance will check the alarms again.

        """
        return self._check_interval_in_seconds

    def set_check_interval_in_seconds(self, check_interval_in_seconds: int) -> None:
        """
        Sets the integer representation of the interval in seconds at which this instance will check the alarms again, default value: 3.

        Args:
            check_interval_in_seconds (int): An integer representing the interval in seconds to check the alarms again.
        """
        self._check_interval_in_seconds = check_interval_in_seconds

    def is_alarm_present(self, alarm_id: str) -> bool:
        """
        Checks if a specific alarm is present in the alarm list.

        Args:
            alarm_id (str): The alarm ID to check for (e.g., '250.001').

        Returns:
            bool: True if the alarm is present, False otherwise.
        """
        alarm_ids = [alarm.get_alarm_id() for alarm in self.alarm_list()]
        return alarm_id in alarm_ids

    def get_ssh_connection(self) -> SSHConnection:
        """
        Gets the SSH connection of this AlarmListKeywords instance.

        Returns:
            SSHConnection: the SSH connection of this AlarmListKeywords instance.

        """
        return self._ssh_connection
