import shlex

from framework.exceptions.keyword_exception import KeywordException
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

    def get_matching_files(self, pattern: str) -> list:
        """Get every file matching the given pattern, distinguishing no match from no answer.

        ``ls`` exits non-zero when a pattern matches nothing, which is an answer rather than a
        failure, so it is reported as an empty list. A return code that could not be read at all
        means the command's fate is unknown, and that is raised: a caller asserting a precondition
        would otherwise report a missing file on a system that never answered.

        Args:
            pattern (str): File pattern to match. Left unquoted so the remote shell expands it.

        Returns:
            list: Matching file paths, empty when the pattern matched nothing.

        Raises:
            KeywordException: If the return code could not be read, meaning the command's outcome
                is unknown rather than negative.
        """
        output = self.ssh_connection.send(f"ls {pattern}")
        return_code = self.ssh_connection.get_return_code()

        if return_code is None or return_code < 0:
            raise KeywordException(f"could not determine the outcome of 'ls {pattern}': return code was {return_code}")
        if return_code != 0:
            return []

        lines = output if isinstance(output, list) else [output or ""]
        return [line.strip() for line in lines if line and line.strip()]

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
