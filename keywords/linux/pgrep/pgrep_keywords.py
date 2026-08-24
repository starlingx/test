"""Linux pgrep command keywords."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class PgrepKeywords(BaseKeyword):
    """Keywords for pgrep process lookup."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize pgrep keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for command execution.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def get_process_count(self, process_name: str) -> int:
        """Get count of running processes matching the name.

        Runs: pgrep -c <process_name>
        Return code 1 means no match (count=0), which is not an error.

        Args:
            process_name (str): Process name to count.

        Returns:
            int: Number of matching processes (0 if none).
        """
        # pgrep -c returns rc=1 when no processes match (count=0).
        # This is expected behavior, not an error — do not add
        # validate_success_return_code here.
        output = self.ssh_connection.send_as_sudo(
            f"pgrep -c {process_name}"
        )
        result = output.strip() if isinstance(output, str) else output[0].strip()
        if result.isdigit():
            return int(result)
        return 0

    def is_process_running(self, process_name: str) -> bool:
        """Check if a process is running.

        Args:
            process_name (str): Process name to check.

        Returns:
            bool: True if at least one matching process is running.
        """
        return self.get_process_count(process_name) > 0

    def get_pids(self, process_name: str) -> list:
        """Get PIDs of all processes matching the name.

        Args:
            process_name (str): Process name to search.

        Returns:
            list: List of PID strings. Empty list if no match.
        """
        # pgrep -c returns rc=1 when no processes match (count=0).
        # This is expected behavior, not an error — do not add
        # validate_success_return_code here.
        output = self.ssh_connection.send_as_sudo(
            f"pgrep {process_name} || true"
        )
        if isinstance(output, str):
            lines = output.strip().split("\n")
        else:
            lines = output
        return [pid.strip() for pid in lines if pid.strip().isdigit()]
