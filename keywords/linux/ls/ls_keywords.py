from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class LsKeywords(BaseKeyword):
    """Keywords for ls command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize ls keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_first_matching_file(self, pattern: str) -> str:
        """Get the first file matching the given pattern.

        Args:
            pattern (str): File pattern to match.

        Returns:
            str: First matching file path.
        """
        output = self.ssh_connection.send(f"ls {pattern}")
        self.validate_success_return_code(self.ssh_connection)

        if isinstance(output, list):
            return output[0].strip()
        return output.strip()
