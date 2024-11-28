import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_object import SystemHostObject
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class SystemHostSwactKeywords(BaseKeyword):
    """
    System Host Swact Keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def host_swact(self):
        """
        Does a swact action.
        Args:

        Returns:

        """
        active_controller = SystemHostListKeywords(self.ssh_connection).get_active_controller()
        standby_controller = SystemHostListKeywords(self.ssh_connection).get_standby_controller()
        self.ssh_connection.send(source_openrc(f'system host-swact {active_controller.get_host_name()}'))
        self.validate_success_return_code(self.ssh_connection)
        is_swact_success = self.wait_for_swact(active_controller, standby_controller)
        if not is_swact_success:
            active_controller = SystemHostListKeywords(self.ssh_connection).get_active_controller()
            standby_controller = SystemHostListKeywords(self.ssh_connection).get_standby_controller()
            raise KeywordException(f"Swact was not successful. Current active controller is {active_controller} " f"and standby controller is {standby_controller}")
        return True

    def wait_for_swact(
        self,
        current_active_controller: SystemHostObject,
        current_standby_controller: SystemHostObject,
        swact_timeout: int = 1800,
    ):
        """
        Waits for the swact action to complete by ensuring the controllers switch active -> standby and standby -> active
        Args:
            current_active_controller (): the current active controller
            current_standby_controller (): the current standby controller
            swact_timeout ():

        Returns:

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
