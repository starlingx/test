from typing import Union

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class CurlResponseKeywords(BaseKeyword):
    """Keywords for curl response validation and processing."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize curl response keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to execute commands.
        """
        self.ssh_connection = ssh_connection

    def get_safe_first_response(self, response: Union[list[str], None]) -> str:
        """Safely get first element from curl response with null/empty checks.

        Args:
            response (Union[list[str], None]): Curl command response (list or None)

        Returns:
            str: First response element stripped, or empty string if invalid
        """
        return response[0].strip() if response and len(response) > 0 else ""
