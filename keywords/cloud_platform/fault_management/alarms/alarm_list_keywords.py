import time

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_output import AlarmListOutput


class AlarmListKeywords(BaseKeyword):
    """
    Class for alarm list keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self._ssh_connection = ssh_connection
        self._check_interval_in_seconds = 3
        self._timeout_in_seconds = 600

    def alarm_list(self) -> [AlarmListObject]:
        """
        Keyword to get all alarms
        Args:

        Returns: the list of alarms

        """
        output = self._ssh_connection.send(source_openrc("fm alarm-list --nowrap"))
        self.validate_success_return_code(self._ssh_connection)
        alarms = AlarmListOutput(output)

        return alarms.get_alarms()

    def wait_for_all_alarms_cleared(self):
        """
        This method waits for all alarms to be cleared in this SSH connection within the period defined by
        'get_timeout_in_seconds()'. Otherwise, this method raises TimeoutError exception.

        Notes:
            The alarms in this SSH connection are checked every 'get_check_interval_in_seconds()' seconds.

        Returns:
           None

        Raises:
            TimeoutError: if some alarm can not be cleared within a period defined by
            'get_timeout_in_seconds()' seconds; False otherwise.

        """
        # Retrieves the current alarms on this SSH connection
        alarms = self.alarm_list()

        now = time.time()
        end_time = now + self.get_timeout_in_seconds()
        while now < end_time:
            if len(alarms) == 0:
                get_logger().log_info(f"All alarms in this SSH connection ({self.get_ssh_connection()}) are now cleared.")
                return
            alarm_ids = ", ".join([alarm.get_alarm_id() for alarm in alarms])
            get_logger().log_info(f"There are still some alarms active in this SSH connection ({self.get_ssh_connection()}). Active alarms IDs: {alarm_ids}. Waiting for {self.get_check_interval_in_seconds():.3f} more seconds. Remaining time: {(end_time - now):.3f} seconds.")
            time.sleep(self.get_check_interval_in_seconds())
            alarms = self.alarm_list()
            now = time.time()

        alarm_ids = ", ".join([alarm.get_alarm_id() for alarm in alarms])
        raise TimeoutError(f"The alarms with the following IDs: {alarm_ids} could not be cleared within {self.get_timeout_in_seconds()} seconds.")

    def wait_for_alarms_cleared(self, alarms: list[AlarmListObject]):
        """
        This method waits for the alarms defined in 'alarms' to be cleared in this SSH connection within the period
        defined by 'get_timeout_in_seconds()'. Otherwise, a TimeoutError exception is raised.

        Notes:
            The alarms in this SSH connection are checked every 'get_check_interval_in_seconds()' seconds.

        Args:
            alarms (list[AlarmListObject]): The list of alarms to be checked to see if they have been cleared in this
            SSH connection.

        Returns:
            None

        Raises:
            TimeoutError: if some alarm can not be cleared within a period defined by
            'get_timeout_in_seconds()' seconds; False otherwise.

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

    def wait_for_alarms_to_appear(self, alarms: list[AlarmListObject]) -> None:
        """
        Waits for the specified alarms to appear on the SSH connection within the timeout
        period defined by 'get_timeout_in_seconds()'. Validates Alarm ID, Reason Text, and Entity ID.

        Args:
            alarms (list[AlarmListObject]): The list of alarms to wait for.

        Returns: None

        Raises:
            TimeoutError: if alarms are not found within the timeout period.
        """
        timeout = self.get_timeout_in_seconds()
        check_interval = self.get_check_interval_in_seconds()
        end_time = time.time() + self.get_timeout_in_seconds()

        alarm_descriptions = ", ".join(f"[ID: {alarm.get_alarm_id()}, Reason: {alarm.get_reason_text()}, Entity: {alarm.get_entity_id()}]" for alarm in alarms)

        while time.time() < end_time:
            current_alarms = self.alarm_list()
            all_matched = all(any(current.get_alarm_id() == expected.get_alarm_id() and current.get_reason_text() == expected.get_reason_text() and current.get_entity_id() == expected.get_entity_id() for current in current_alarms) for expected in alarms)

            if all_matched:
                get_logger().log_info(f"All expected alarms are now present in SSH connection ({self.get_ssh_connection()}): {alarm_descriptions}")
                return

            get_logger().log_info(f"Waiting for expected alarms to appear in SSH connection ({self.get_ssh_connection()}). " f"Retrying in {check_interval:.3f} seconds. Remaining time: {end_time - time.time():.3f} seconds.")
            time.sleep(check_interval)

        raise TimeoutError(f"The following alarms did not appear within {timeout} seconds: {alarm_descriptions}")

    def get_timeout_in_seconds(self) -> int:
        """
        Gets an integer representing the maximum time in seconds to wait for the alarms to be cleared.
        Default value: 600.

        Returns:
            (int): An integer representing the maximum time in seconds to wait for the alarms to be cleared.
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
        Gets an integer representing the interval in seconds at which this instance will check the alarms again.
        Default value: 3.

        Returns:
            (int): An integer representing the interval in seconds at which this instance will check the alarms again.

        """
        return self._check_interval_in_seconds

    def set_check_interval_in_seconds(self, check_interval_in_seconds: int) -> int:
        """
        Sets the integer representation of the interval in seconds at which this instance will check the alarms again.
        Default value: 3.

        Returns:
            (int): An integer representing the interval in seconds at which this instance will check the alarms again.

        """
        return self._check_interval_in_seconds

    def get_ssh_connection(self):
        """
        Gets the SSH connection of this AlarmListKeywords instance.
        Returns:
            SSHConnection: the SSH connection of this AlarmListKeywords instance.

        """
        return self._ssh_connection
