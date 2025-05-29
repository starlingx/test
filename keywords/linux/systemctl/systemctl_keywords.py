from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class SystemCTLKeywords(BaseKeyword):
    """
    Keywords for systemctl stop/start/restart <service_name> cmds
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def systemctl_start(self, service_name: str, instance_name: str) -> None:
        """
        Starts a systemd service instance remotely using systemctl.

        Args:
            service_name (str): The base name of the service (e.g., 'ptp4l').
            instance_name (str): The specific instance name (e.g., 'ptp1').

        Returns: None
        """
        self.ssh_connection.send_as_sudo(f"systemctl start {service_name}@{instance_name}.service")

    def systemctl_stop(self, service_name: str, instance_name: str) -> None:
        """
        Stops a systemd service instance remotely using systemctl.

        Args:
            service_name (str): The base name of the service (e.g., 'ptp4l').
            instance_name (str): The specific instance name (e.g., 'ptp1').

        Returns: None
        """
        self.ssh_connection.send_as_sudo(f"systemctl stop {service_name}@{instance_name}.service")

    def systemctl_restart(self, service_name: str, instance_name: str) -> None:
        """
        Restarts a systemd service instance remotely using systemctl.

        Args:
            service_name (str): The base name of the service (e.g., 'ptp4l').
            instance_name (str): The specific instance name (e.g., 'ptp1').

        Returns: None
        """
        self.ssh_connection.send_as_sudo(f"systemctl restart {service_name}@{instance_name}.service")
