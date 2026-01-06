from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class PkillKeywords(BaseKeyword):
    """Keywords for pkill process management."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize pkill keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for command execution.
        """
        self.ssh_connection = ssh_connection

    def pkill_by_pattern(self, pattern: str) -> None:
        """Kill processes matching the specified pattern.

        Args:
            pattern (str): Pattern to match processes against.
        """
        cmd = f"pkill -f {pattern} || true"
        self.ssh_connection.send(cmd)

    def pkill_by_name(self, process_name: str) -> None:
        """Kill processes by exact process name.

        Args:
            process_name (str): Exact process name to kill.
        """
        cmd = f"pkill {process_name} || true"
        self.ssh_connection.send(cmd)
