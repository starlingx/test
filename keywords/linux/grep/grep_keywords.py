from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class GrepKeywords(BaseKeyword):
    """Generic Grep command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize find keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for grep operations.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def grep_and_extract_fields(self, pattern: str, file_path: str, tail_lines: Optional[int] = None, field_indices: Optional[list] = None) -> str:
        """Grep pattern from file and extract specific fields.

        Args:
            pattern (str): Pattern to search for.
            file_path (str): File path to search in.
            tail_lines (Optional[int]): Number of lines from tail. Defaults to None.
            field_indices (Optional[list]): Field indices to extract (1-based). Defaults to None.

        Returns:
            str: Extracted fields as string.
        """
        cmd = f'grep "{pattern}" {file_path}'

        if tail_lines:
            cmd += f" | tail -{tail_lines}"

        if field_indices:
            awk_fields = ", ".join([f"\${i}" for i in field_indices])
            cmd += f' | awk "{{print {awk_fields}}}"'

        output = self.ssh_connection.send(cmd)

        if isinstance(output, list):
            filtered_output = [line.strip().rstrip(":") for line in output if line.strip()]
            return filtered_output[0] if len(filtered_output) == 1 else filtered_output
        return output.strip().rstrip(":") if output and output.strip() else ""
