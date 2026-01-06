from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_list_output import DcManagerSubcloudPeerGroupListOutput


class DcManagerSubcloudPeerGroupListKeywords(BaseKeyword):
    """Keywords for 'dcmanager subcloud-peer-group list' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_peer_group_list(self) -> DcManagerSubcloudPeerGroupListOutput:
        """Get subcloud peer group list using 'dcmanager subcloud-peer-group list' command.

        Returns:
            DcManagerSubcloudPeerGroupListOutput: Parsed peer group list output.
        """
        cmd = "dcmanager subcloud-peer-group list"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return DcManagerSubcloudPeerGroupListOutput(output)
