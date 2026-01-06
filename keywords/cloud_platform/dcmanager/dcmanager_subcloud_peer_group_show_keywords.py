from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_peer_group_show_output import DcManagerSubcloudPeerGroupShowOutput


class DcManagerSubcloudPeerGroupShowKeywords(BaseKeyword):
    """Keywords for 'dcmanager subcloud-peer-group show' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_peer_group_show(self, identifier: str) -> DcManagerSubcloudPeerGroupShowOutput:
        """Gets the 'cmanager subcloud-peer-group show' output.

        Args:
            identifier (str): The identifier to show details for

        Returns:
            DcManagerSubcloudPeerGroupShowOutput: Parsed peer group show output.

        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud-peer-group show {identifier}"))
        self.validate_success_return_code(self.ssh_connection)
        return DcManagerSubcloudPeerGroupShowOutput(output)
