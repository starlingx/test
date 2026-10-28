from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class SystemCTLKeywords(BaseKeyword):
    """
    Keywords for systemctl stop/start/restart <service_name> cmds
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def _build_unit_name(self, service_name: str, instance_name: str = None) -> str:
        """Build the systemd unit name for a plain or templated service.

        Args:
            service_name (str): The base name of the service (e.g., 'ptp4l', 'ipsec').
            instance_name (str, optional): The instance name for a templated unit
                (e.g., 'ptp1'). When omitted, a plain unit name is returned.

        Returns:
            str: The full unit name, e.g. 'ptp4l@ptp1.service' or 'ipsec.service'.
        """
        if instance_name:
            return f"{service_name}@{instance_name}.service"
        return f"{service_name}.service"

    def systemctl_start(self, service_name: str, instance_name: str = None) -> None:
        """
        Starts a systemd service remotely using systemctl.

        Args:
            service_name (str): The base name of the service (e.g., 'ptp4l', 'ipsec').
            instance_name (str, optional): The instance name for a templated unit
                (e.g., 'ptp1'). Omit for a plain (non-templated) service.

        Returns: None
        """
        self.ssh_connection.send_as_sudo(f"systemctl start {self._build_unit_name(service_name, instance_name)}")

    def systemctl_stop(self, service_name: str, instance_name: str = None) -> None:
        """
        Stops a systemd service remotely using systemctl.

        Args:
            service_name (str): The base name of the service (e.g., 'ptp4l', 'ipsec').
            instance_name (str, optional): The instance name for a templated unit
                (e.g., 'ptp1'). Omit for a plain (non-templated) service.

        Returns: None
        """
        self.ssh_connection.send_as_sudo(f"systemctl stop {self._build_unit_name(service_name, instance_name)}")

    def systemctl_restart(self, service_name: str, instance_name: str = None) -> None:
        """
        Restarts a systemd service remotely using systemctl.

        Args:
            service_name (str): The base name of the service (e.g., 'ptp4l', 'ipsec').
            instance_name (str, optional): The instance name for a templated unit
                (e.g., 'ptp1'). Omit for a plain (non-templated) service.

        Returns: None
        """
        self.ssh_connection.send_as_sudo(f"systemctl restart {self._build_unit_name(service_name, instance_name)}")
