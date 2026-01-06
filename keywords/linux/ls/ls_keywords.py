from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
import shlex


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

    def list_directory_contents(self, directory_path: str, max_entries: int = -1) -> list:
        """List directory contents with detailed information.

        Args:
            directory_path (str): Directory path to list.
            max_entries (int): Maximum number of entries to return. Defaults to -1.

        Returns:
            list: List of directory entries with detailed information.
        """
        cmd = f"ls -la {shlex.quote(directory_path)}"
        
        if max_entries > 0:
            cmd += f" | head -{max_entries}"

        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        
        if isinstance(output, list):
            return [line.strip() for line in output if line.strip()]
        return [output.strip()] if output.strip() else []
