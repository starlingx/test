from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class WhichKeywords(BaseKeyword):
    """Keywords for which command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
        """
        self._ssh_connection: SSHConnection = ssh_connection

    def which_process(self, process: str) -> str:
        """
        Verify that a process is accessible in PATH.

        Args:
            process (str): process name to check. eg: virtctl

        Returns:
            str: Path to the process.

        Raises:
            Exception: If process is not found in PATH.
        """
        get_logger().log_info(f"Verifying {process} is accessible in PATH")
        output = self._ssh_connection.send(f"bash -lc 'which {process}'")
        self.validate_success_return_code(self._ssh_connection)
        return output
