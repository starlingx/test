"""Keywords for wget command operations."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class WgetKeywords(BaseKeyword):
    """Keywords for downloading files using wget."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize WgetKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
        """
        self.ssh_connection: SSHConnection = ssh_connection

    def download_file(self, url: str, destination: str, command_timeout: int = 600) -> str:
        """Download a file from a URL to a destination path on the remote host.

        Args:
            url (str): URL of the file to download.
            destination (str): Absolute path on the remote host where the file will be saved.
            command_timeout (int): Timeout in seconds for the download. Defaults to 600.

        Returns:
            str: Command output.

        Raises:
            AssertionError: If the download command fails.
        """
        get_logger().log_info(f"Downloading {url} to {destination}")
        output = self.ssh_connection.send(
            f"wget -q --no-check-certificate -O {destination} {url}",
            command_timeout=command_timeout,
        )
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"Successfully downloaded file to {destination}")
        return output
