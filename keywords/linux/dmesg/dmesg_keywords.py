from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_str_contains
from keywords.base_keyword import BaseKeyword


class DmesgKeywords(BaseKeyword):
    """Keywords for dmesg command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize dmesg keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_dmesg(self) -> str:
        """Get full dmesg output.

        Returns:
            str: Complete kernel ring buffer output.
        """
        return self.ssh_connection.send_as_sudo("dmesg")

    def get_dmesg_tail(self, lines: int = 20) -> str:
        """Get last N lines of dmesg output.

        Args:
            lines (int): Number of lines to retrieve. Defaults to 20.

        Returns:
            str: Last N lines of kernel ring buffer output.
        """
        return self.ssh_connection.send_as_sudo(f"dmesg | tail -{lines}")

    def verify_dmesg_contains(self, expected_message: str, lines: int = 1) -> None:
        """Verify dmesg output contains expected message.

        Args:
            expected_message (str): Message to search for in dmesg output.
            lines (int): Number of lines to check from tail. Defaults to 1.
        """
        dmesg_output = self.get_dmesg_tail(lines=lines)
        if isinstance(dmesg_output, list):
            dmesg_output = "".join(dmesg_output)
        validate_str_contains(dmesg_output, expected_message, f"dmesg should contain '{expected_message}'")
