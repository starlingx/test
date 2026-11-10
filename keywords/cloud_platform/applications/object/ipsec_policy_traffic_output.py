"""Checked nonce-correlated traffic response."""

import json

from framework.exceptions.keyword_exception import KeywordException
from keywords.python.string import String


class IPsecPolicyTrafficOutput:
    """Reject empty, malformed, stale or wrong-peer traffic evidence."""

    def __init__(self, content: str | list[str], expected: dict):
        """Parse and validate an exact traffic response.

        Args:
            content (str | list[str]): Checked client command output.
            expected (dict): Independently requested flow and nonce.
        """
        try:
            self.response = json.loads(String.normalize_command_output(content))
        except (ValueError, TypeError) as error:
            raise KeywordException("Empty or malformed traffic evidence") from error
        if self.response != expected:
            raise KeywordException("Traffic returned wrong-peer, wrong-port or stale evidence")

    def get_nonce(self) -> str:
        """Return verified nonce.

        Returns:
            str: Validated response field.
        """
        return self.response["nonce"]

    def get_server(self) -> str:
        """Return verified server.

        Returns:
            str: Validated response field.
        """
        return self.response["server"]

    def get_protocol(self) -> str:
        """Return verified protocol.

        Returns:
            str: Validated response field.
        """
        return self.response["protocol"]

    def get_port(self) -> int:
        """Return verified port.

        Returns:
            int: Validated response field.
        """
        return self.response["port"]

    def get_count(self) -> int:
        """Return verified count.

        Returns:
            int: Validated response field.
        """
        return self.response["count"]

    def get_address(self) -> str:
        """Return verified address.

        Returns:
            str: Validated response field.
        """
        return self.response["address"]
