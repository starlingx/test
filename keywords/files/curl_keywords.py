from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class CurlKeywords(BaseKeyword):
    """Keywords that wrap the `curl` CLI for use on the SSH-connected host."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize with SSH connection.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host that will run curl.
        """
        self.ssh_connection = ssh_connection

    def download_via_curl(self, url: str, destination: str, timeout: int = 600) -> str:
        """Download a file from a URL onto the SSH-connected host using curl.

        Runs `curl -sL -o {destination} {url}` on the remote host. Validates
        the return code, so a failed download (network error, 404, disk full)
        raises an exception instead of silently returning an empty file path.

        Args:
            url (str): The HTTP/HTTPS URL to download from.
            destination (str): Full path on the remote host where the file should be saved.
            timeout (int): Seconds to wait for the download to complete (default 600).

        Returns:
            str: The destination path (same as input, returned for fluent use).
        """
        get_logger().log_info(f"Downloading: {url} -> {destination}")
        self.ssh_connection.send(
            f"curl -sL -o {destination} {url}",
            command_timeout=timeout,
            reconnect_timeout=0,
        )
        self.validate_success_return_code(self.ssh_connection)
        return destination
