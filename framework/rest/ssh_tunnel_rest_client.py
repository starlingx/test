import threading
import time
from urllib.parse import urlparse

import paramiko
import requests
from urllib3.exceptions import InsecureRequestWarning

from config.configuration_manager import ConfigurationManager
from framework.rest.paramiko_forward_server import _find_free_port, _ParamikoForwardServer
from framework.rest.rest_response import RestResponse


class SSHTunnelRestClient:
    """REST client that routes HTTP requests through a paramiko-based port forwarder.

    Uses the same paramiko jump host connection mechanism as SSHConnection
    (direct-tcpip channels) rather than the sshtunnel library, which is
    incompatible with this jump host configuration.

    One forwarder is created per unique remote port and reused for all
    subsequent requests to that port.
    """

    # Class-level state shared across all instances
    _jump_client: paramiko.SSHClient = None
    _forwarders: dict = {}  # remote_port -> (forwarder, local_port)
    _lock = threading.Lock()

    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    @classmethod
    def _get_jump_transport(cls) -> paramiko.Transport:
        """Return a live paramiko transport to the jump host, connecting if needed.

        Returns:
            paramiko.Transport: Active transport for the jump host connection.

        Raises:
            Exception: If the jump host connection cannot be established.
        """
        with cls._lock:
            if cls._jump_client and cls._jump_client.get_transport() and cls._jump_client.get_transport().is_active():
                return cls._jump_client.get_transport()

            config = ConfigurationManager.get_lab_config()
            jump_host_config = config.get_jump_host_configuration()

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

            retries = 3
            retry_delay = 5
            last_exception = None
            for attempt in range(1, retries + 1):
                try:
                    client.connect(
                        jump_host_config.get_host(),
                        port=jump_host_config.get_ssh_port(),
                        username=jump_host_config.get_credentials().get_user_name(),
                        password=jump_host_config.get_credentials().get_password(),
                        timeout=30,
                        allow_agent=True,
                        look_for_keys=True,
                    )
                    cls._jump_client = client
                    return client.get_transport()
                except Exception as exception:
                    last_exception = exception
                    if attempt < retries:
                        time.sleep(retry_delay)

            raise last_exception

    @classmethod
    def _get_forwarder_for_port(cls, remote_host: str, remote_port: int) -> int:
        """Return the local port of a forwarder to the given remote host:port.

        Creates the forwarder if it doesn't exist or has stopped.

        Args:
            remote_host (str): The remote host to forward to.
            remote_port (int): The remote port to forward to.

        Returns:
            int: The local port to connect to.
        """
        with cls._lock:
            existing = cls._forwarders.get(remote_port)
            if existing:
                forwarder, local_port = existing
                if forwarder.is_alive():
                    return local_port
                forwarder.stop()
                del cls._forwarders[remote_port]

        # Get transport outside the lock to avoid deadlock with _get_jump_transport
        transport = cls._get_jump_transport()

        with cls._lock:
            # Double-check after acquiring lock
            existing = cls._forwarders.get(remote_port)
            if existing:
                forwarder, local_port = existing
                if forwarder.is_alive():
                    return local_port

            local_port = _find_free_port()
            forwarder = _ParamikoForwardServer(local_port, remote_host, remote_port, transport)
            forwarder.start()
            cls._forwarders[remote_port] = (forwarder, local_port)
            return local_port

    def _rewrite_url(self, url: str) -> str:
        """Rewrite a URL to route through the paramiko port forwarder.

        Args:
            url (str): The original URL targeting the lab host.

        Returns:
            str: The rewritten URL pointing to localhost via the forwarder.
        """
        config = ConfigurationManager.get_lab_config()
        if not config.is_use_jump_server():
            return url

        parsed = urlparse(url)
        remote_host = config.get_floating_ip()

        if ":" in parsed.netloc:
            _, port_str = parsed.netloc.rsplit(":", 1)
            try:
                remote_port = int(port_str)
            except ValueError:
                return url
        else:
            remote_port = 443

        local_port = self._get_forwarder_for_port(remote_host, remote_port)
        modified_url = url.replace(parsed.netloc, f"127.0.0.1:{local_port}", 1)
        return modified_url

    def _normalize_headers(self, headers: dict | list | None) -> dict:
        """Convert headers to dictionary format.

        Args:
            headers (dict | list | None): Headers in dict or list-of-dicts format.

        Returns:
            dict: Normalized headers dictionary.
        """
        if not headers:
            return {}
        if isinstance(headers, dict):
            return headers
        if isinstance(headers, list):
            headers_dict = {}
            for header in headers:
                if isinstance(header, dict):
                    headers_dict.update(header)
            return headers_dict
        return {}

    # Keep _create_tunnel_for_url for any callers that use it directly
    def _create_tunnel_for_url(self, url: str) -> tuple:
        """Compatibility shim — rewrites the URL using the paramiko forwarder.

        Args:
            url (str): The original URL.

        Returns:
            tuple: (modified_url, None)
        """
        return self._rewrite_url(url), None

    def get(self, url: str, headers: dict | list | None = None) -> RestResponse:
        """Run a GET request through the paramiko port forwarder.

        Args:
            url (str): The URL to GET.
            headers (dict | list | None): Optional request headers.

        Returns:
            RestResponse: The response.
        """
        headers_dict = self._normalize_headers(headers)
        modified_url = self._rewrite_url(url)
        response = requests.get(modified_url, headers=headers_dict, verify=False)
        return RestResponse(response)

    def post(self, url: str, data: str | bytes | dict, headers: dict | list | None) -> RestResponse:
        """Run a POST request through the paramiko port forwarder.

        Args:
            url (str): The URL to POST to.
            data (str | bytes | dict): The request body.
            headers (dict | list | None): Request headers.

        Returns:
            RestResponse: The response.
        """
        headers_dict = self._normalize_headers(headers)
        modified_url = self._rewrite_url(url)
        response = requests.post(modified_url, headers=headers_dict, data=data, verify=False)
        return RestResponse(response)

    def close(self) -> None:
        """Stop all port forwarders and close the jump host connection."""
        with SSHTunnelRestClient._lock:
            for _, (forwarder, _) in list(SSHTunnelRestClient._forwarders.items()):
                forwarder.stop()
            SSHTunnelRestClient._forwarders.clear()
            if SSHTunnelRestClient._jump_client:
                try:
                    SSHTunnelRestClient._jump_client.close()
                except Exception:
                    pass
                SSHTunnelRestClient._jump_client = None
