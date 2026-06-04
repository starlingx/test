from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class DrbdKeywords(BaseKeyword):
    """Keywords for DRBD (Distributed Replicated Block Device) status operations."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize DrbdKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def get_drbd_status(self) -> str:
        """Read /proc/drbd and return its contents as a string.

        Returns:
            str: Contents of /proc/drbd showing DRBD connection and sync status.
        """
        output = self.ssh_connection.send("cat /proc/drbd")
        self.validate_success_return_code(self.ssh_connection)
        if isinstance(output, list):
            return "\n".join(output)
        return output
