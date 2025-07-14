import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class SystemHostRebootKeywords(BaseKeyword):
    """
    System Host Reboot Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): the ssh connection
        """
        self.ssh_connection = ssh_connection

    def host_reboot(self, host_name: str) -> bool:
        """
        Does a swact action.

        Args:
            host_name (str): the host to reboot

        Returns:
            bool: true if successful

        """
        # check that host is locked before attempting reboot
        host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
        if not (host_value.get_availability() == "online" and host_value.get_administrative() == "locked" and host_value.get_operational() == "disabled"):
            raise KeywordException("Host must be in locked state before running reboot")

        pre_uptime_of_host = SystemHostListKeywords(self.ssh_connection).get_uptime(host_name)

        self.ssh_connection.send(source_openrc(f"system host-reboot {host_name}"))
        self.validate_success_return_code(self.ssh_connection)

        is_reboot_success = self.wait_for_reboot(host_name, pre_uptime_of_host)
        if not is_reboot_success:
            raise KeywordException(f"Reboot of {host_name} was not successful")
        return True

    def wait_for_reboot(
        self,
        host_name: str,
        prev_uptime: int,
        reboot_timeout: int = 1800,
    ) -> bool:
        """
        Waits for the swact action to complete by ensuring the controllers switch active -> standby and standby -> active

        Args:
            host_name (str): host name that is rebooted
            prev_uptime (int): the uptime before the reboot
            reboot_timeout (int):

        Returns:
            bool: True if reboot completes in given time

        """
        timeout = time.time() + reboot_timeout
        refresh_time = 5

        while time.time() < timeout:
            try:
                host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
                current_uptime = SystemHostListKeywords(self.ssh_connection).get_uptime(host_name)
                if host_value.get_availability() == "online" and host_value.get_administrative() == "locked" and host_value.get_operational() == "disabled" and 0 < current_uptime < prev_uptime:
                    return True
            except Exception:
                get_logger().log_info(f"Found an exception when running system host list command. " f"Trying again after {refresh_time} seconds")

            time.sleep(refresh_time)

        return False

    def wait_for_force_reboot(
        self,
        host_name: str,
        prev_uptime: int,
        reboot_timeout: int = 1800,
    ) -> bool:
        """
        Waits for the forced reboot action to complete by ensuring the rebooted host becomes online, available and enabled.

        Args:
            host_name (str): host name that is force rebooted
            prev_uptime (int): the uptime before the forced reboot
            reboot_timeout (int): the reboot timeout

        Returns:
            bool: True if reboot is successful
        """
        timeout = time.time() + reboot_timeout
        refresh_time = 5

        while time.time() < timeout:
            try:
                host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
                current_uptime = SystemHostListKeywords(self.ssh_connection).get_uptime(host_name)
                if host_value.get_availability() == "available" and host_value.get_administrative() == "unlocked" and host_value.get_operational() == "enabled" and current_uptime < prev_uptime:
                    return True
            except Exception:
                get_logger().log_info(f"Found an exception when running system host list command. " f"Trying again after {refresh_time} seconds")

            time.sleep(refresh_time)

        return False
