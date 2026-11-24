"""CurlKeywords keywords."""

import re
import shlex
from typing import Optional

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

    def get_http_status_code(self, url: str, insecure: bool = True, cacert: str = None, user: str = None, host_header: Optional[str] = None) -> str:
        """Get HTTP response status code from a URL.

        Args:
            url (str): Target URL to check.
            insecure (bool): Skip TLS verification (-k flag). Defaults to True.
            cacert (str): Path to CA cert file for verification. Overrides insecure.
            user (str): Username:password for basic auth.
            host_header (Optional[str]): Value for the HTTP Host header, for host-based routing checks
                (e.g. Gateway/Ingress routes that share one address). Optional.

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
        if host_header:
            flags += f" -H {shlex.quote(f'Host: {host_header}')}"
        cmd = f"curl {flags} {url}"
        output = self.ssh_connection.send(cmd)
        raw = "".join(output) if isinstance(output, list) else output
        http_code = raw.strip().strip("'")[-3:]
        get_logger().log_info(f"curl {url} -> HTTP {http_code}")
        return http_code

    def find_file_in_directory_listing(self, url: str, name_pattern: str, extension: str, exclude_pattern: Optional[str] = None) -> str:
        """Find the name of a file in the HTML directory listing served at a URL.

        Fetches the listing with curl on the SSH-connected host and returns the
        first file name that starts with name_pattern and ends with extension,
        in the order the server lists them.

        Args:
            url (str): URL of the directory listing.
            name_pattern (str): grep basic regular expression the file name starts with (e.g. 'my-app-[0-9]').
            extension (str): File extension the name ends with, matched literally (e.g. '.tgz').
            exclude_pattern (Optional[str]): grep basic regular expression of names to skip
                (e.g. 'debug'). Defaults to None, which skips nothing.

        Returns:
            str: The file name (e.g. 'my-app-1.0-0.tgz').

        Raises:
            RuntimeError: If no file name in the listing matches, including when the listing cannot be fetched.
        """
        # A name in a listing link ends at the closing quote of href or at the next tag.
        match_expression = f'{name_pattern}[^"<]*{re.escape(extension)}'
        cmd = f"curl -s {shlex.quote(url)} | grep -o {shlex.quote(match_expression)}"
        if exclude_pattern:
            cmd += f" | grep -v {shlex.quote(exclude_pattern)}"
        cmd += " | head -1"
        get_logger().log_info(f"Looking for '{name_pattern}...{extension}' in the directory listing of {url}")
        output = self.ssh_connection.send(cmd)
        file_name = ("".join(output) if isinstance(output, list) else output).strip()
        if not file_name:
            raise RuntimeError(f"No file matching '{name_pattern}...{extension}' found in the directory listing of {url}. Check the URL and that the host can reach it.")
        get_logger().log_info(f"Found '{file_name}' in the directory listing of {url}")
        return file_name
