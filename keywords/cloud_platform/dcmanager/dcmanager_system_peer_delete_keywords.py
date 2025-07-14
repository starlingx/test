from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class DcManagerSystemPeerDeleteKeywords(BaseKeyword):
    """Keywords for 'dcmanager system-peer delete' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_system_peer_delete(self, peer_identifier: str) -> None:
        """Delete a system peer using 'dcmanager system-peer delete' command.

        Args:
            peer_identifier (str): Name or ID of the system peer to delete.
        """
        cmd = f"dcmanager system-peer delete {peer_identifier}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
