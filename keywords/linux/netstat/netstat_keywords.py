from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class NetstatKeywords(BaseKeyword):
    """Keywords for netstat network monitoring."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize netstat keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for command execution.
        """
        self.ssh_connection = ssh_connection

    def is_port_listening(self, port: int) -> bool:
        """Check if a port is listening.

        Args:
            port (int): Port number to check.

        Returns:
            bool: True if port is listening.
        """
        cmd = f"netstat -ln | grep :{port} || echo 'not_found'"
        result = self.ssh_connection.send(cmd)
        return "not_found" not in " ".join(result)
