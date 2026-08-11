"""CurlKeywords keywords."""

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

    def get_http_status_code(self, url: str, insecure: bool = True, cacert: str = None, user: str = None) -> str:
        """Get HTTP response status code from a URL.

        Args:
            url (str): Target URL to check.
            insecure (bool): Skip TLS verification (-k flag). Defaults to True.
            cacert (str): Path to CA cert file for verification. Overrides insecure.
            user (str): Username:password for basic auth.

        Returns:
            str: HTTP status code (e.g., "200", "401", "503").
        """
        flags = "-s -o /dev/null -w '%{http_code}'"
        if cacert:
            flags += f" --cacert {cacert}"
        elif insecure:
            flags += " -k"
        if user:
            flags += f" -u {user}"
        cmd = f"curl {flags} {url}"
        output = self.ssh_connection.send(cmd)
        raw = "".join(output) if isinstance(output, list) else output
        http_code = raw.strip().strip("'")[-3:]
        get_logger().log_info(f"curl {url} -> HTTP {http_code}")
        return http_code
