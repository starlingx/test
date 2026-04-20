import threading
from typing import Optional

from sshtunnel import SSHTunnelForwarder

from config.host.objects.host_configuration import HostConfiguration
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_tunnel_info import SSHTunnelInfo


class SSHTunnel:
    """Class to create an SSH tunnel with optional jump host support."""

    def __init__(
        self,
        tunnel_info: SSHTunnelInfo,
        host: str,
        ssh_port: int,
        username: str,
        password: str,
        jump_host_config: Optional[HostConfiguration] = None,
    ):
        self._host: str = host
        self._ssh_port: int = ssh_port
        self._username: str = username
        self._password: str = password
        self._tunnel_info: SSHTunnelInfo = tunnel_info
        self._jump_host_config: Optional[HostConfiguration] = jump_host_config
        self._jump_server_tunnel: Optional[SSHTunnelForwarder] = None
        self._tunnel: Optional[SSHTunnelForwarder] = None
        self._lock = threading.Lock()

        # create ssh tunnel
        self._ssh_address_or_host = (self._host, self._ssh_port)

    def __enter__(self):
        """Context manager entry: create the tunnel."""
        if not self.create_tunnel():
            raise ConnectionError(f"Failed to create SSH tunnel: {self._tunnel_info!s}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: close the tunnel."""
        self.close()
        return False  # Do not suppress exceptions

    def get_tunnel_info(self) -> SSHTunnelInfo:
        """Getter for tunnel_info"""
        return self._tunnel_info

    def set_tunnel_info(self, tunnel_info: SSHTunnelInfo):
        """Setter for tunnel_info"""
        self._tunnel_info = tunnel_info

    def _create_jump_box_tunnel(self) -> bool:
        """Create a ssh tunnel through the jump server

        Returns:
            bool: True if successful, or if there is no need to do so
                  False if the creating of the tunnel fails
        """
        if not self._jump_host_config:
            # DO NOTHING
            return True

        try:
            self._jump_server_tunnel = SSHTunnelForwarder(
                (self._jump_host_config.get_host(), self._jump_host_config.get_ssh_port()),
                ssh_username=self._jump_host_config.get_credentials().get_user_name(),
                ssh_password=self._jump_host_config.get_credentials().get_password(),
                remote_bind_address=(self._host, self._ssh_port),
                local_bind_address=(self._tunnel_info.get_local_bind_address(), self._tunnel_info.get_local_ports()[-1]),
            )
            self._jump_server_tunnel.start()
            get_logger().log_info(f"SSH tunnel created through jump box:\n{self._jump_server_tunnel!s}")

        except Exception as e:
            get_logger().log_error(f"Failed to create SSH tunnel through jump server:\n{self._jump_host_config!s}\n {e}")
            return False

        self._ssh_address_or_host = (self._tunnel_info.get_local_bind_address(), self._tunnel_info.get_local_ports()[-1])
        return True

    def create_tunnel(self) -> bool:
        """Create an SSH tunnel (port forwarding) from local to remote.

        Returns:
            bool: True if successful, False otherwise.
        """
        with self._lock:
            if not self._create_jump_box_tunnel():
                return False
            try:
                self._tunnel = SSHTunnelForwarder(
                    ssh_address_or_host=self._ssh_address_or_host,
                    ssh_username=self._username,
                    ssh_password=self._password,
                    local_bind_address=(self._tunnel_info.get_local_bind_address(), self._tunnel_info.get_local_ports()[0]),
                    remote_bind_address=(self._tunnel_info.get_remote_host(), self._tunnel_info.get_remote_port()),
                )
                self._tunnel.start()
                get_logger().log_info(f"SSH tunnel created: {self._tunnel_info!s}\n{self._tunnel!s}")
            except Exception as e:
                get_logger().log_error(f"Failed to create SSH tunnel: {self._tunnel_info!s}\n {e}")
                return False
            return True

    def close(self) -> None:
        """Close SSH tunnel."""
        with self._lock:
            if self._jump_server_tunnel:
                self._jump_server_tunnel.stop()
                self._jump_server_tunnel = None
            if self._tunnel:
                self._tunnel.stop()
                self._tunnel = None
        get_logger().log_info(f"Closed SSH tunnel: {self._tunnel_info!s}")
