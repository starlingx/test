import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class SystemHostRebootKeywords(BaseKeyword):
    """
    System Host Reboot Keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def host_reboot(self, host_name: str):
        """
        Does a swact action.
        Args:
            host_name (): the host to reboot

        Returns:

        """

        # check that host is locked before attempting reboot
        host_value = SystemHostListKeywords().get_system_host_list(self.ssh_connection).get_host(host_name)
        if not (host_value.get_availability() == 'online' and host_value.get_administrative() == 'locked' and host_value.get_operational() == 'disabled'):
            raise KeywordException("Host must be in locked state before running reboot")

        pre_uptime_of_host = SystemHostListKeywords().get_uptime(self.ssh_connection, host_name)

        self.ssh_connection.send(source_openrc(f'system host-reboot {host_name}'))
        self.validate_success_return_code(self.ssh_connection)
        is_reboot_success = self.wait_for_reboot(self.ssh_connection, host_name, pre_uptime_of_host)
        if not is_reboot_success:
            raise KeywordException(f"Reboot of {host_name} was not successful")
        return True

    def wait_for_reboot(
        self,
        host_name: str,
        prev_uptime: int,
        reboot_timeout: int = 1800,
    ):
        """
        Waits for the swact action to complete by ensuring the controllers switch active -> standby and standby -> active
        Args:
            host_name (): host name that is rebooted
            prev_uptime (): the uptime before the reboot
            reboot_timeout ():

        Returns:

        """
        timeout = time.time() + reboot_timeout
        refresh_time = 5

        while time.time() < timeout:
            try:
                host_value = SystemHostListKeywords().get_system_host_list(self.ssh_connection).get_host(host_name)
                current_uptime = SystemHostListKeywords().get_uptime(self.ssh_connection, host_name)
                if host_value.get_availability() == 'online' and host_value.get_administrative() == 'locked' and host_value.get_operational() == 'disabled' and current_uptime < prev_uptime:
                    return True
            except Exception:
                get_logger().log_info(f"Found an exception when running system host list command. " f"Trying again after {refresh_time} seconds")

            time.sleep(refresh_time)

        return False
