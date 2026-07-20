from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class LogGrepKeywords(BaseKeyword):
    """Keywords for searching log files that require sudo access."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize LogGrepKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def grep_log_for_errors(self, log_path: str, pattern: str, secondary_pattern: Optional[str] = None, tail: int = 5) -> str:
        """Grep a log file for error patterns using sudo, returning matching lines.

        Uses ``SSHConnection.send_as_sudo_non_interactive()`` to access log files
        not readable by sysadmin. Returns an empty string if no matches are found
        (uses '|| true' to avoid non-zero exit codes).

        Args:
            log_path (str): Absolute path to the log file to search.
            pattern (str): Primary grep pattern (case-insensitive).
            secondary_pattern (Optional[str]): Optional secondary grep pattern to
                further filter results (case-insensitive). Defaults to None.
            tail (int): Number of trailing lines to return. Defaults to 5.

        Returns:
            str: Matching log lines, or empty string if no matches found.
        """
        if secondary_pattern:
            grep_pipeline = f'grep -i "{pattern}" {log_path} 2>/dev/null ' f'| grep -i "{secondary_pattern}" ' f"| tail -{tail} || true"
        else:
            grep_pipeline = f'grep -i "{pattern}" {log_path} 2>/dev/null ' f"| tail -{tail} || true"

        output = self.ssh_connection.send_as_sudo_non_interactive(f"sh -c '{grep_pipeline}'")
        if isinstance(output, list):
            return "\n".join(output).strip()
        return output.strip()
