import time

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class SystemHostPowerKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-power-*' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
        """
        self.ssh_connection = ssh_connection

    def host_power_off(self, host_name: str, timeout: int = 600):
        """
        Powers off a host

        Args:
            host_name (str): Name of the host to power off.
            timeout (int): Timeout in seconds to wait for the host to power off.
        """
        self.ssh_connection.send(source_openrc(f"system host-power-off {host_name}"))
        self.validate_success_return_code(self.ssh_connection)

        self.wait_for_host_power_off(host_name, timeout)

    def host_power_on(self, host_name: str, timeout: int = 600):
        """
        Powers on a host

        Args:
            host_name (str): Name of the host to power on.
            timeout (int): Timeout in seconds to wait for the host to power on.
        """
        self.ssh_connection.send(source_openrc(f"system host-power-on {host_name}"))
        self.validate_success_return_code(self.ssh_connection)

        self.wait_for_host_powered_on(host_name, timeout)

    def wait_for_host_power_off(self, host_name: str, timeout: int = 600) -> bool:
        """
        Waits for a host to reach power-off state

        Args:
            host_name (str): Name of the host.
            timeout (int): Timeout in seconds.

        Returns:
            bool: True if host reaches power-off state.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                host = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
                if host.get_availability() == "power-off":
                    return True
            except Exception:
                get_logger().log_info("Exception checking host status, retrying...")
            time.sleep(10)

        raise TimeoutError(f"Timeout waiting for host '{host_name}' to power off")

    def wait_for_host_powered_on(self, host_name: str, timeout: int = 600) -> bool:
        """
        Waits for a host to be powered on and available

        Args:
            host_name (str): Name of the host.
            timeout (int): Timeout in seconds.

        Returns:
            bool: True if host reaches expected state.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                host = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
                if host.get_availability() == "online" and host.get_administrative() == "locked":
                    return True
            except Exception:
                get_logger().log_info("Exception checking host status, retrying...")
            time.sleep(10)

        raise TimeoutError(f"Timeout waiting for host '{host_name}' to power on")
