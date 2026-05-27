from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject


class SystemRestoreCompleteKeywords(BaseKeyword):
    """Provides keyword functions for the 'system restore-complete' command.

    This keyword runs 'system restore-complete' after all nodes have been
    unlocked during a standalone system restore, then waits for the
    'restore in progress' alarm to be cleared.
    """

    RESTORE_IN_PROGRESS_ALARM_ID = "250.008"

    def __init__(self, ssh_connection: SSHConnection):
        """Initializes SystemRestoreCompleteKeywords with an SSH connection.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
        """
        self.ssh_connection = ssh_connection

    def system_restore_complete(self, timeout: int = 1800) -> bool:
        """Executes 'system restore-complete' and waits for the restore alarm to clear.

        This should be called after all nodes have been successfully unlocked
        during a standalone system restore. The command signals to the platform
        that the restore process is finished, and the system will clear the
        'restore in progress' alarm (250.008) once all restore operations
        have completed.

        Args:
            timeout (int): Maximum time in seconds to wait for the restore
                alarm to be cleared. Defaults to 1800 (30 minutes).

        Returns:
            bool: True if restore-complete succeeded and the alarm was cleared.

        Raises:
            AssertionError: If the 'system restore-complete' command fails.
            TimeoutError: If the restore alarm is not cleared within the timeout.
        """
        get_logger().log_info("Executing 'system restore-complete'")
        self.ssh_connection.send(source_openrc("system restore-complete"))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("'system restore-complete' command executed successfully")

        get_logger().log_info(f"Waiting for restore in progress alarm ({self.RESTORE_IN_PROGRESS_ALARM_ID}) to be cleared")
        self._wait_for_restore_alarm_cleared(timeout)
        get_logger().log_info("Restore in progress alarm cleared - system restore is complete")

        return True

    def _wait_for_restore_alarm_cleared(self, timeout: int) -> None:
        """Waits for the restore in progress alarm to be cleared.

        Args:
            timeout (int): Maximum time in seconds to wait for the alarm to clear.

        Raises:
            TimeoutError: If the alarm is not cleared within the timeout.
        """
        restore_alarm = AlarmListObject()
        restore_alarm.set_alarm_id(self.RESTORE_IN_PROGRESS_ALARM_ID)

        alarm_keywords = AlarmListKeywords(self.ssh_connection)
        alarm_keywords.set_timeout_in_seconds(timeout)
        alarm_keywords.wait_for_alarms_cleared([restore_alarm])
