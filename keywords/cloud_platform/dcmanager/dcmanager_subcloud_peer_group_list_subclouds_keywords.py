from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_list_subclouds_output import DcManagerSubcloudPeerGroupListSubcloudsOutput


class DcManagerSubcloudPeerGroupListSubcloudsKeywords(BaseKeyword):
    """Keywords for 'dcmanager subcloud-peer-group list-subclouds' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_peer_group_list_subclouds(self, identifier: str) -> DcManagerSubcloudPeerGroupListSubcloudsOutput:
        """Get subclouds in peer group.

        Args:
            identifier (str): Peer group identifier (id or name).

        Returns:
            DcManagerSubcloudPeerGroupListSubcloudsOutput: Parsed subclouds list output.
        """
        cmd = f"dcmanager subcloud-peer-group list-subclouds {identifier}"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return DcManagerSubcloudPeerGroupListSubcloudsOutput(output)
