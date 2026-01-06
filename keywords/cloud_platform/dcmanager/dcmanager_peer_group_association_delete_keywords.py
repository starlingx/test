from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class DcManagerPeerGroupAssociationDeleteKeywords(BaseKeyword):
    """Keywords for 'dcmanager peer-group association delete' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_peer_group_association_delete(self, association_id: int) -> None:
        """Delete a peer group association using 'dcmanager peer-group-association delete' command.

        Args:
            association_id (int): ID of the peer group association to delete.
        """
        cmd = f"dcmanager peer-group-association delete {association_id}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
