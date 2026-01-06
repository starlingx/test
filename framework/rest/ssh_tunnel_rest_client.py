import socket
from urllib.parse import urlparse

import requests
from sshtunnel import SSHTunnelForwarder
from urllib3.exceptions import InsecureRequestWarning

from config.configuration_manager import ConfigurationManager
from framework.rest.rest_response import RestResponse


class SSHTunnelRestClient:
    """
    REST client that creates SSH tunnels on-demand for each API call
    """

    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    def _create_tunnel_for_url(self, url):
        """Create SSH tunnel for the specific URL and return modified URL"""
        config = ConfigurationManager.get_lab_config()
        if not config.is_use_jump_server():
            return url, None

        parsed = urlparse(url)

        # Extract port from URL
        if ":" in parsed.netloc:
            host, port_str = parsed.netloc.rsplit(":", 1)
            try:
                remote_port = int(port_str)
            except ValueError:
                return url, None
        else:
            remote_port = 443

        # Get jump host config
        jump_host_config = config.get_jump_host_configuration()
        lab_ip = config.get_floating_ip()

        # Find free local port
        local_port = self._find_free_port()

        # Create tunnel
        tunnel = SSHTunnelForwarder((jump_host_config.get_host(), jump_host_config.get_ssh_port()), ssh_username=jump_host_config.get_credentials().get_user_name(), ssh_password=jump_host_config.get_credentials().get_password(), remote_bind_address=(lab_ip, remote_port), local_bind_address=("127.0.0.1", local_port))

        tunnel.start()

        # Return modified URL and tunnel
        modified_url = url.replace(f"{parsed.netloc}", f"127.0.0.1:{local_port}")
        return modified_url, tunnel

    def _find_free_port(self):
        """Find an available local port"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

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

    def get(self, url: str, headers=None) -> RestResponse:
        """Runs a get request with SSH tunnel created on-demand"""
        headers_dict = self._normalize_headers(headers)
        modified_url, tunnel = self._create_tunnel_for_url(url)

        try:
            response = requests.get(modified_url, headers=headers_dict, verify=False)
            return RestResponse(response)
        finally:
            if tunnel:
                tunnel.stop()

    def post(self, url: str, data, headers) -> RestResponse:
        """Runs a post request with SSH tunnel created on-demand"""
        headers_dict = self._normalize_headers(headers)
        modified_url, tunnel = self._create_tunnel_for_url(url)

        try:
            response = requests.post(modified_url, headers=headers_dict, data=data, verify=False)
            return RestResponse(response)
        finally:
            if tunnel:
                tunnel.stop()

    def close(self):
        """No-op for compatibility - tunnels are created and destroyed on-demand per API call"""
        pass
