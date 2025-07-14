from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_peer_group_association_show_output import DcManagerPeerGroupAssociationShowOutput


class DcManagerPeerGroupAssociationShowKeywords(BaseKeyword):
    """Keywords for 'dcmanager peer-group-association show' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_peer_group_association_show(self, association_id: int) -> DcManagerPeerGroupAssociationShowOutput:
        """Show a peer group association using 'dcmanager peer-group-association show' command.

        Args:
            association_id (int): ID of the peer group association to show.

        Returns:
            DcManagerPeerGroupAssociationShowOutput: Parsed output of the peer group association show command.
        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager peer-group-association show {association_id}"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_system_peer_group_association_show_output = DcManagerPeerGroupAssociationShowOutput(output)

        return dcmanager_system_peer_group_association_show_output
