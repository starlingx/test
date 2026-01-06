from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_status_output import DcManagerSubcloudPeerGroupStatusOutput


class DcManagerSubcloudPeerGroupStatusKeywords(BaseKeyword):
    """Keywords for 'dcmanager subcloud-peer-group status' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_peer_group_status(self, identifier: str) -> DcManagerSubcloudPeerGroupStatusOutput:
        """Get subcloud peer group status using 'dcmanager subcloud-peer-group status' command.

        Args:
            identifier (str): The peer group ID or name to get status for.

        Returns:
            DcManagerSubcloudPeerGroupStatusOutput: Parsed peer group status output.
        """
        cmd = f"dcmanager subcloud-peer-group status {identifier}"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return DcManagerSubcloudPeerGroupStatusOutput(output)
