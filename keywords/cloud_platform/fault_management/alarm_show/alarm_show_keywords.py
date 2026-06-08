"""Keywords for fm alarm-show command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarm_show.objects.alarm_show_output import AlarmShowOutput


class AlarmShowKeywords(BaseKeyword):
    """Keywords for the fm alarm-show command."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize AlarmShowKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
        """
        self.ssh_connection = ssh_connection

    def alarm_show(self, alarm_uuid: str) -> AlarmShowOutput:
        """Run fm alarm-show for a given UUID and return parsed object.

        Args:
            alarm_uuid (str): UUID of the alarm to show.

        Returns:
            AlarmShowOutput: Parsed alarm details.
        """
        output = self.ssh_connection.send(source_openrc(f"fm alarm-show {alarm_uuid}"))
        self.validate_success_return_code(self.ssh_connection)
        return AlarmShowOutput(output)
