import socket
import ipaddress
from contextlib import suppress

class SSHTunnelInfo:
    """
    Class to represent a SSH Tunnel
    """

    # Constructor
    def __init__(
        self,
        remote_host: str,
        remote_port: int,
        local_bind_address: str = '127.0.0.1',
        local_ports: tuple[int, int] = (),  # If jump server is used we will need 2 ssh tunnels
    ):
        self._remote_host: str = remote_host
        self._remote_port: int = remote_port
        self._local_bind_address: str = local_bind_address

        if not local_ports:
            self._local_ports: tuple[int, int] = SSHTunnelInfo.get_free_local_ports()

    def __repr__(self):
        return f"{vars(self)}"

    def __str__(self):
        local_port, _ = self._local_ports
        return f"'{self.get_local_bind_address()}:{local_port}' -> '{self.get_remote_host()}:{self.get_remote_port()}'"

    def get_local_ports(self) -> tuple[int, int]:
        return self._local_ports

    def set_local_ports(self, local_ports: tuple[int, int]):
        self._local_ports = local_ports

    def get_local_bind_address(self) -> str:
        return self._local_bind_address

    def set_local_bind_address(self, local_bind_address: str):
        self._local_bind_address = local_bind_address

    def get_remote_port(self) -> int:
        return self._remote_port

    def set_remote_port(self, remote_port: int):
        self._remote_port = remote_port

    def get_remote_host(self) -> str:
        return self._remote_host

    def set_remote_host(self, remote_host: str):
        self._remote_host = remote_host

    def get_local_base_url(self) -> str:
        """Gets a base url of the local end of the tunnel

        Returns:
            str: The base url to local port
        """
        # default ipv4
        local_port, _ = self._local_ports
        url = f"{self.get_local_bind_address()}:{local_port}"
        with suppress(ValueError):
            ipaddress.IPv6Address(self.get_local_bind_address())
            url = f"[{self.get_local_bind_address()}]:{local_port}"
        return url

    @staticmethod
    def get_free_local_ports() -> tuple[int, int]:
        """Find and return two free local ports."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s1:
            s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s1.bind(('', 0))
            port1 = s1.getsockname()[1]
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
                s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s2.bind(('', 0))
                port2 = s2.getsockname()[1]
        return port1, port2

    @staticmethod
    def get_free_local_port() -> int:
        """Find and return a free local port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
