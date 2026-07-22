"""Keyword for watching subcloud state transitions across one or more subclouds."""

import time
from typing import List, Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords

# Deploy operation in-progress states (dcmanager subcloud add / deploy)
DEPLOY_IN_PROGRESS_STATES = ["creating", "pre-install", "installing", "bootstrapping", "configuring", "deploying"]

# Rehome operation in-progress states (dcmanager subcloud add --migrate)
REHOME_IN_PROGRESS_STATES = ["pre-rehome", "rehoming"]

# Enroll operation in-progress states (dcmanager subcloud add --enroll / deploy enroll)
ENROLL_IN_PROGRESS_STATES = ["pre-enroll", "start-enroll-init", "initiating-enroll", "enrolling"]

# Backup operation in-progress states (dcmanager subcloud-backup create)
BACKUP_IN_PROGRESS_STATES = ["validating", "backing-up"]

# Restore operation in-progress states (dcmanager subcloud-backup restore)
RESTORE_IN_PROGRESS_STATES = ["pre-install", "installing", "restoring"]

# Prestage operation in-progress states (dcmanager subcloud prestage)
PRESTAGE_IN_PROGRESS_STATES = ["prestaging-packages", "prestaging-images", "prestaging"]


class DcManagerSubcloudStateWatcherKeywords(BaseKeyword):
    """Watches subclouds transition through states until completion or failure.

    Polls dcmanager subcloud list and monitors a specified field until all
    watched subclouds leave their in-progress states and reach either the
    complete state or a failed state.

    Supports watching a single subcloud or a batch of subclouds simultaneously.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the system controller.
        """
        self.ssh_connection = ssh_connection
        self._list_kw = DcManagerSubcloudListKeywords(ssh_connection)

    def watch_subclouds(
        self,
        subcloud_names: List[str],
        field_to_watch: str,
        in_progress_states: List[str],
        complete_state: str,
        failed_states: Optional[List[str]] = None,
        timeout: int = 4800,
        polling_interval: int = 30,
    ) -> None:
        """Watch multiple subclouds transition through states until all complete or fail.

        Polls dcmanager subcloud list at the specified interval and checks the
        given field for each subcloud. Continues polling while any subcloud is
        in an in-progress state. Raises on failure or timeout.

        Args:
            subcloud_names (List[str]): Names of subclouds to watch.
            field_to_watch (str): Field to monitor. One of: deploy_status,
                availability, sync, backup_status, prestage_status.
            in_progress_states (List[str]): States that indicate the operation
                is still running (e.g. ["creating", "installing", "bootstrapping"]).
            complete_state (str): Target state indicating success (e.g. "complete").
            failed_states (Optional[List[str]]): States indicating failure. If None,
                any state containing "failed" is treated as a failure.
            timeout (int): Maximum seconds to wait for all subclouds. Defaults to 4800.
            polling_interval (int): Seconds between polls. Defaults to 60.

        Raises:
            TimeoutError: If not all subclouds reach a terminal state within timeout.
            Exception: If any subcloud reaches a failed state.
        """
        if not subcloud_names:
            raise ValueError("subcloud_names must not be empty.")

        pending = set(subcloud_names)
        completed = []
        failed = []
        end_time = time.time() + timeout

        get_logger().log_info(f"Watching {len(subcloud_names)} subcloud(s) for '{field_to_watch}' to reach '{complete_state}'")
        get_logger().log_info(f"In-progress states: {in_progress_states}")

        while pending and time.time() < end_time:
            sc_list_output = self._list_kw.get_dcmanager_subcloud_list()
            finished_this_round = []

            for sc_name in pending:
                if not sc_list_output.is_subcloud_in_output(sc_name):
                    continue

                sc_obj = sc_list_output.get_subcloud_by_name(sc_name)
                current_state = self._get_field_value(sc_obj, field_to_watch)

                if current_state == complete_state:
                    get_logger().log_info(f"Subcloud '{sc_name}' reached '{complete_state}'")
                    completed.append(sc_name)
                    finished_this_round.append(sc_name)
                elif self._is_failed_state(current_state, failed_states):
                    get_logger().log_info(f"Subcloud '{sc_name}' entered failed state: '{current_state}'")
                    failed.append((sc_name, current_state))
                    finished_this_round.append(sc_name)
                elif current_state not in in_progress_states:
                    get_logger().log_info(f"Subcloud '{sc_name}' in unexpected state: '{current_state}'")
                    failed.append((sc_name, current_state))
                    finished_this_round.append(sc_name)

            for sc_name in finished_this_round:
                pending.remove(sc_name)

            if pending:
                self._log_status_summary(sc_list_output, pending, field_to_watch, len(completed), failed)
                time.sleep(polling_interval)

        if pending:
            msg = f"Timed out waiting for subclouds to reach '{complete_state}'. Still pending: {sorted(pending)}"
            get_logger().log_error(msg)
            raise TimeoutError(msg)

        if failed:
            failed_summary = ", ".join([f"{name} ({state})" for name, state in failed])
            msg = f"Subclouds failed: {failed_summary}"
            get_logger().log_error(msg)
            raise Exception(msg)

        get_logger().log_info(f"All {len(completed)} subcloud(s) reached '{complete_state}'")

    def watch_single_subcloud(
        self,
        subcloud_name: str,
        field_to_watch: str,
        in_progress_states: List[str],
        complete_state: str,
        failed_states: Optional[List[str]] = None,
        timeout: int = 4800,
        polling_interval: int = 60,
    ) -> None:
        """Watch a single subcloud transition through states.

        Convenience wrapper around watch_subclouds for single subcloud operations.

        Args:
            subcloud_name (str): Name of the subcloud to watch.
            field_to_watch (str): Field to monitor.
            in_progress_states (List[str]): States indicating operation is running.
            complete_state (str): Target success state.
            failed_states (Optional[List[str]]): States indicating failure.
            timeout (int): Maximum seconds to wait. Defaults to 4800.
            polling_interval (int): Seconds between polls. Defaults to 60.

        Raises:
            TimeoutError: If the subcloud doesn't reach a terminal state within timeout.
            Exception: If the subcloud reaches a failed state.
        """
        self.watch_subclouds(
            subcloud_names=[subcloud_name],
            field_to_watch=field_to_watch,
            in_progress_states=in_progress_states,
            complete_state=complete_state,
            failed_states=failed_states,
            timeout=timeout,
            polling_interval=polling_interval,
        )

    @staticmethod
    def _get_field_value(sc_obj: object, field_to_watch: str) -> str:
        """Get the value of the specified field from a subcloud list object.

        Args:
            sc_obj: DcManagerSubcloudListObject instance.
            field_to_watch (str): Field name to retrieve.

        Returns:
            str: Current value of the field.

        Raises:
            ValueError: If the field is not supported.
        """
        field_map = {
            "deploy_status": "get_deploy_status",
            "availability": "get_availability",
            "sync": "get_sync",
            "management": "get_management",
            "backup_status": "get_backup_status",
            "prestage_status": "get_prestage_status",
        }
        getter_name = field_map.get(field_to_watch)
        if getter_name is None:
            raise ValueError(f"Unsupported field_to_watch: '{field_to_watch}'. Supported: {list(field_map.keys())}")
        return getattr(sc_obj, getter_name)()

    @staticmethod
    def _is_failed_state(state: str, failed_states: Optional[List[str]]) -> bool:
        """Determine if a state is a failure state.

        Args:
            state (str): Current state to check.
            failed_states (Optional[List[str]]): Explicit list of failed states,
                or None to use the default "contains failed" heuristic.

        Returns:
            bool: True if the state is a failure.
        """
        if failed_states is not None:
            return state in failed_states
        return "failed" in state

    @staticmethod
    def _log_status_summary(sc_list_output: object, pending: set, field_to_watch: str, completed_count: int, failed: list) -> None:
        """Log an aggregated status summary of all watched subclouds.

        Args:
            sc_list_output: DcManagerSubcloudListOutput instance.
            pending (set): Set of subcloud names still being watched.
            field_to_watch (str): Field being monitored.
            completed_count (int): Number of subclouds that have already completed.
            failed (list): List of (name, state) tuples for failed subclouds.
        """
        state_counts = {}
        for sc_name in sorted(pending):
            if sc_list_output.is_subcloud_in_output(sc_name):
                sc_obj = sc_list_output.get_subcloud_by_name(sc_name)
                state = DcManagerSubcloudStateWatcherKeywords._get_field_value(sc_obj, field_to_watch)
                state_counts[state] = state_counts.get(state, 0) + 1

        for _, fail_state in failed:
            state_counts[fail_state] = state_counts.get(fail_state, 0) + 1

        total = len(pending) + completed_count + len(failed)
        summary_lines = [f"Operation: In-progress | Total: {total}"]
        if completed_count > 0:
            summary_lines.append(f"  completed = {completed_count}")
        for state, count in sorted(state_counts.items()):
            summary_lines.append(f"  {state} = {count}")

        get_logger().log_info("\n".join(summary_lines))
