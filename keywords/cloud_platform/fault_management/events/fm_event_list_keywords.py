from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.events.objects.fm_event_list_output import FmEventListOutput


class FmEventListKeywords(BaseKeyword):
    """Class for 'fm event-list' keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_event_list(self, limit: int = 0) -> FmEventListOutput:
        """
        Get list of fault management events.

        Args:
            limit (int): Maximum number of events to return. 0 means no limit.

        Returns:
            FmEventListOutput: Parsed event list output.
        """
        limit_flag = f" --limit {limit}" if limit > 0 else ""
        cmd = f"fm event-list --nowrap{limit_flag}"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return FmEventListOutput(output)
