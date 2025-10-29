import time

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class SMKeywords(BaseKeyword):
    """
    Class for SM keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def sm_restart(self, service_name: str):
        """
        Runs the sm-restart service command

        Args:
            service_name (str): the service name

        """
        self.ssh_connection.send_as_sudo(f"sm-restart service {service_name}")
        self.validate_success_return_code(self.ssh_connection)

    def sm_query(self, service_name: str) -> str:
        """
        Runs the sm-dump service command and return the service status

        Args:
            service_name (str): the service name

        Returns:
            str: service status

        """
        service_status = self.ssh_connection.send(f"sm-query service {service_name}")
        return str(service_status)

    def is_service_enabled(self, service_name: str) -> bool:
        """
        Returns true if the host is enabled or not

        Args:
            service_name (str): the service name

        Returns:
            bool: True if service is enabled else False

        """
        service_status = self.sm_query(service_name)
        if "enabled-active" in service_status:
            return True
        else:
            return False

    def wait_for_service_enabled(self, service_name: str, restart_timeout: int = 60) -> bool:
        """
        Waits for the given service to be enabled

        Args:
            service_name (str): the service name
            restart_timeout (int): the service restart timeout

        Returns:
            bool: True if service is enabled successfully

        """
        timeout = time.time() + restart_timeout

        while time.time() < timeout:
            if self.is_service_enabled(service_name):
                return True
            time.sleep(1)

        return False

    def restart_sysinv(self) -> None:
        """
        Restart sysinv services

        """
        self.sm_restart("sysinv-inv")
        self.sm_restart("sysinv-conductor")
        is_enabled = self.wait_for_service_enabled("sysinv-inv")
        if not is_enabled:
            raise RuntimeError("sysinv-inv was not enabled successfully.")
        is_enabled = self.wait_for_service_enabled("sysinv-conductor")
        if not is_enabled:
            raise RuntimeError("sysinv-conductor was not enabled successfully.")
