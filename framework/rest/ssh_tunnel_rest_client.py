import socket
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from sshtunnel import SSHTunnelForwarder
from urllib3.exceptions import InsecureRequestWarning

from config.configuration_manager import ConfigurationManager
from framework.rest.rest_response import RestResponse


class SSHTunnelRestClient:
    """
    REST client that makes HTTP requests through SSH tunnel when jump host is configured
    """

    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self._tunnels = {}
        self._port_mappings = {}
        self._setup_tunnels()

    def _setup_tunnels(self):
        """Setup SSH tunnels for common API ports if jump host is configured"""
        config = ConfigurationManager.get_lab_config()

        if not config.is_use_jump_server():
            return

        # Get jump host configurations
        jump_host_config = ConfigurationManager.get_lab_config().get_jump_host_configuration()
        lab_ip = config.get_floating_ip()

        # Get API ports from configuration
        rest_api_config = ConfigurationManager.get_rest_api_config()
        api_ports = rest_api_config.get_all_ports()

        for remote_port in api_ports:
            local_port = self._find_free_port()

            # Create SSH tunnel for this port
            tunnel = SSHTunnelForwarder((jump_host_config.get_host(), jump_host_config.get_ssh_port()), ssh_username=jump_host_config.get_credentials().get_user_name(), ssh_password=jump_host_config.get_credentials().get_password(), remote_bind_address=(lab_ip, remote_port), local_bind_address=("127.0.0.1", local_port))

            # Start the tunnel
            tunnel.start()

            # Store tunnel and port mapping
            self._tunnels[remote_port] = tunnel
            self._port_mappings[remote_port] = local_port

    def _find_free_port(self):
        """Find an available local port"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def _modify_url_for_tunnel(self, url):
        """Modify URL to use local tunnel if configured"""
        if not self._tunnels:
            return url

        parsed = urlparse(url)

        # Extract the port from the URL
        if ":" in parsed.netloc:
            host, port_str = parsed.netloc.rsplit(":", 1)
            try:
                remote_port = int(port_str)
            except ValueError:
                return url
        else:
            # Default HTTPS port
            remote_port = 443

        # Check if we have a tunnel for this port
        if remote_port in self._port_mappings:
            local_port = self._port_mappings[remote_port]
            modified_url = url.replace(f"{parsed.netloc}", f"127.0.0.1:{local_port}")
            return modified_url

        return url

    def _normalize_headers(self, headers):
        """Convert headers to dictionary format"""
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

    def get(self, url: str, headers: Optional[Any] = None) -> RestResponse:
        """
        Runs a get request with the given url and headers, tunneling through SSH if configured

        Args:
            url (str): The URL for the request.
            headers (Optional[Any]): Headers for the request (dict or list of dicts). Defaults to None.

        Returns:
            RestResponse: An object representing the response of the GET request.
        """
        # Convert headers to dict format
        headers_dict = self._normalize_headers(headers)

        # Modify URL for tunnel if needed
        modified_url = self._modify_url_for_tunnel(url)

        response = requests.get(modified_url, headers=headers_dict, verify=False)
        return RestResponse(response)

    def post(self, url: str, data: Any, headers: Any) -> RestResponse:
        """
        Runs a post request with the given url and headers, tunneling through SSH if configured

        Args:
            url (str): The URL for the request.
            data (Any): The data to be sent in the body of the request.
            headers (Any): Headers for the request (dict or list of dicts).

        Returns:
            RestResponse: An object containing the response from the request.
        """
        # Convert headers to dict format
        headers_dict = self._normalize_headers(headers)

        # Modify URL for tunnel if needed
        modified_url = self._modify_url_for_tunnel(url)

        response = requests.post(modified_url, headers=headers_dict, data=data, verify=False)
        return RestResponse(response)

    def close(self):
        """Close all SSH tunnels if they exist"""
        for tunnel in self._tunnels.values():
            tunnel.stop()
        self._tunnels.clear()
        self._port_mappings.clear()
