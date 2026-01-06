from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class DcManagerSubcloudPeerGroupDeleteKeywords(BaseKeyword):
    """Keywords for 'dcmanager subcloud-peer-group delete' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_peer_group_delete(self, identifier: str) -> None:
        """Delete a subcloud peer group using 'dcmanager subcloud-peer-group delete' command.

        Args:
            identifier (str): The identifier to delete id / peer_group_name.
        """
        cmd = f"dcmanager subcloud-peer-group delete {identifier}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
