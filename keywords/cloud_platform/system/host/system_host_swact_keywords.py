import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_object import SystemHostObject
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class SystemHostSwactKeywords(BaseKeyword):
    """
    System Host Swact Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection to use.
        """
        self.ssh_connection = ssh_connection

    def host_swact(self, swact_accepted_timeout: int = 300) -> bool:
        """
        Performs a controller switchover action (swact).

        Args:
            swact_accepted_timeout (int): timeout trying the swact

        Returns:
            bool: True if swact was successful, raises exception otherwise.
        """
        active_controller = SystemHostListKeywords(self.ssh_connection).get_active_controller()
        standby_controller = SystemHostListKeywords(self.ssh_connection).get_standby_controller()
        self.ssh_connection.send(source_openrc(f"system host-swact {active_controller.get_host_name()}"))

        # Checking whether the host can be swacted; if not, the process will retry until the timeout is reached.
        start = time.time()
        while time.time() - start < swact_accepted_timeout:
            if self.ssh_connection.get_return_code() == 1:
                get_logger().log_info("Fail to swact, trying again in 5 seconds")
                time.sleep(5)
                self.ssh_connection.send(source_openrc(f"system host-swact {active_controller.get_host_name()}"))
            else:
                get_logger().log_info(f"The swact of host {active_controller} to {standby_controller} was started")
                break
        else:
            raise KeywordException(f"Timeout: failed to swact host {active_controller}")

        self.validate_success_return_code(self.ssh_connection)
        is_swact_success = self.wait_for_swact(active_controller, standby_controller)
        if not is_swact_success:
            active_controller = SystemHostListKeywords(self.ssh_connection).get_active_controller()
            standby_controller = SystemHostListKeywords(self.ssh_connection).get_standby_controller()
            raise KeywordException(f"Swact was not successful. Current active controller is {active_controller} " f"and standby controller is {standby_controller}")
        return True

    def host_swact_force(self) -> bool:
        """
        Performs a controller force switchover action (swact).

        Returns:
            bool: True if swact --force was successful, raises exception otherwise.
        """
        active_controller = SystemHostListKeywords(self.ssh_connection).get_active_controller()
        standby_controller = SystemHostListKeywords(self.ssh_connection).get_standby_controller()
        self.ssh_connection.send(source_openrc(f"system host-swact --force {active_controller.get_host_name()}"))
        self.validate_success_return_code(self.ssh_connection)
        is_swact_success = self.wait_for_swact(active_controller, standby_controller)
        if not is_swact_success:
            active_controller = SystemHostListKeywords(self.ssh_connection).get_active_controller()
            standby_controller = SystemHostListKeywords(self.ssh_connection).get_standby_controller()
            raise KeywordException(f"Force swact was not successful. Current active controller is {active_controller} " f"and standby controller is {standby_controller}")
        return True

    def wait_for_swact(
        self,
        current_active_controller: SystemHostObject,
        current_standby_controller: SystemHostObject,
        swact_timeout: int = 1800,
    ) -> bool:
        """
        Waits for the swact action to complete by ensuring the controllers switch active -> standby and standby -> active.

        Args:
            current_active_controller (SystemHostObject): The current active controller.
            current_standby_controller (SystemHostObject): The current standby controller.
            swact_timeout (int): Timeout in seconds to wait for swact completion.

        Returns:
            bool: True if swact completed successfully, False otherwise.
        """
        timeout = time.time() + swact_timeout
        refresh_time = 5

        while time.time() < timeout:
            try:
                active_controller = SystemHostListKeywords(self.ssh_connection).get_active_controller()
                standby_controller = SystemHostListKeywords(self.ssh_connection).get_standby_controller()
                if active_controller.get_host_name() == current_standby_controller.get_host_name() and standby_controller.get_host_name() == current_active_controller.get_host_name():
                    return True
            except Exception:
                get_logger().log_info(f"Found an exception when running system host list command. " f"Trying again after {refresh_time} seconds")

            time.sleep(refresh_time)

        return False
