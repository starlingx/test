from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class DcManagerSystemPeerAddKeywords(BaseKeyword):
    """Keywords for 'dcmanager system-peer add' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def dcmanager_system_peer_add(
        self,
        peer_uuid: str,
        peer_name: str,
        manager_endpoint: str,
        peer_controller_gateway_address: str,
        manager_password: str,
        manager_username: Optional[str] = None,
        administrative_state: Optional[bool] = None,
    ) -> None:
        """Add a system peer using 'dcmanager system-peer add' command.

        Args:
            peer_uuid (str): UUID of the peer system.
            peer_name (str): Name of the peer system.
            manager_endpoint (str): Manager endpoint URL.
            peer_controller_gateway_address (str): Controller gateway IP address.
            manager_password (str): Manager password for authentication.
            manager_username (Optional[str]): Manager username for authentication.
            administrative_state (Optional[bool]): Administrative state (enabled/disabled).
        """
        cmd_parts = [
            "dcmanager system-peer add",
            f"--peer-uuid {peer_uuid}",
            f"--peer-name {peer_name}",
            f"--manager-endpoint {manager_endpoint}",
            f"--peer-controller-gateway-address {peer_controller_gateway_address}",
            f"--manager-password {manager_password}",
        ]

        if manager_username:
            cmd_parts.append(f"--manager-username {manager_username}")

        if administrative_state is not None:
            state = "enabled" if administrative_state else "disabled"
            cmd_parts.append(f"--administrative-state {state}")

        cmd = " ".join(cmd_parts)
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
