import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class SystemHostReinstallKeywords(BaseKeyword):
    """
    Keywords for System Reinstall Host commands
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): the ssh connection
        """
        self.ssh_connection = ssh_connection

    def wait_for_host_reinstall(self, host_name: str, reinstall_wait_timeout: int = 1800) -> bool:
        """
        Wait for the host to be reinstalled

        Args:
            host_name (str): the host name
            reinstall_wait_timeout (int): the amount of time in secs to wait for the host to reinstall

        Returns:
            bool: True if host is reinstalled

        """
        timeout = time.time() + reinstall_wait_timeout
        refresh_time = 5

        while time.time() < timeout:

            try:
                if self.is_host_reinstalled(host_name):
                    return True
            except Exception:
                get_logger().log_info(f"Found an exception when checking the health of the system. Trying again after {refresh_time} seconds")

            time.sleep(refresh_time)
        return False

    def is_host_reinstalled(self, host_name: str) -> bool:
        """
        Returns true if the host is reinstalled

        Args:
            host_name (str): the name of the host

        Returns:
            bool: True is host is reinstalled

        """
        is_host_list_ok = False

        # Check System Host-List
        host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)

        if host_value.get_availability() == "online" and host_value.get_administrative() == "locked" and host_value.get_operational() == "disabled":
            get_logger().log_info("The host is in a good state from system host list.")
            is_host_list_ok = True

        # Exit the loop once all conditions are met.
        if is_host_list_ok:
            return True

        return False

    def reinstall_host(self, host_name: str) -> bool:
        """
        Reinstall the given host

        Args:
            host_name (str): the host name

        Returns:
            bool: True if the reinstalled is successful

        Raises:
            KeywordException: If reinstall does not occur in the given time

        """
        self.ssh_connection.send(source_openrc(f"system host-reinstall {host_name}"))
        self.validate_success_return_code(self.ssh_connection)
        validate_equals_with_retry(lambda: SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name).get_availability(), expected_value="offline", validation_description="Waiting for host to go offline", timeout=500)
        is_host_reinstalled = self.wait_for_host_reinstall(host_name)
        if not is_host_reinstalled:
            host_value = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(host_name)
            raise KeywordException("Host reinstall did not complete within the required time. Host values were: " f"Operational: {host_value.get_operational()} " f"Administrative: {host_value.get_administrative()} " f"Availability: {host_value.get_availability()}")
        return True
