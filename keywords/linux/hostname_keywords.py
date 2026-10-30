"""Read host identity using a checked SSH command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class HostnameKeywords(BaseKeyword):
    """Read the hostname of the connected host."""

    def __init__(self, ssh_connection: SSHConnection):
        """Store the host connection.

        Args:
            ssh_connection (SSHConnection): Connection to the host being identified.
        """
        self.ssh_connection = ssh_connection

    def get_hostname(self) -> str:
        """Read and normalize the hostname after validating command success.

        Returns:
            str: Hostname reported by the connected host.
        """
        output = self.ssh_connection.send("hostname")
        self.validate_success_return_code(self.ssh_connection)
        text = "\n".join(line.rstrip("\n") for line in output) if isinstance(output, list) else output
        return text.strip()
