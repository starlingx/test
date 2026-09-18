from typing import List

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_list_contains_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_object import SystemHostObject
from keywords.cloud_platform.system.host.objects.system_host_output import SystemHostOutput


class SystemHostListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host list' command.

    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH Connection object
        """
        self.ssh_connection = ssh_connection

    def get_system_host_list(self) -> SystemHostOutput:
        """
        Gets the system host list

        Returns:
            SystemHostOutput: object represents the system host-list command output
        """
        output = self.ssh_connection.send(source_openrc("system host-list"))
        self.validate_success_return_code(self.ssh_connection)
        system_host_output = SystemHostOutput(output)

        return system_host_output

    def get_standby_controller(self) -> SystemHostObject:
        """
        Gets the standby controller

        Returns:
            SystemHostObject: standby controller object in system host-list command output
        """
        system_host_output = self.get_system_host_with_extra_column(["capabilities"])
        standby_controller = system_host_output.get_standby_controller()

        return standby_controller

    def get_active_controller(self) -> SystemHostObject:
        """
        Gets the active controller

        Returns:
            SystemHostObject: active controller object in system host-list command output
        """
        system_host_output = self.get_system_host_with_extra_column(["capabilities"])
        active_controller = system_host_output.get_active_controller()

        return active_controller

    def is_active_controller(self, host: str) -> bool:
        """
        Return True when the named host is currently the active controller.

        The platform refuses to lock an active controller ("Can not lock an active controller"),
        so a deploy has to know this before locking anything.

        Args:
            host(str): the hostname to check.

        Returns:
            bool: True when the host is the active controller.

        """
        return self.get_active_controller().get_host_name() == host

    def get_controllers(self) -> [SystemHostObject]:
        """
        Gets all controllers

        Returns:
            [SystemHostObject]: List of controller objects
        """
        system_host_output = self.get_system_host_with_extra_column(["capabilities"])
        return system_host_output.get_controllers()

    def get_computes(self) -> [SystemHostObject]:
        """
        Gets the computes

        Returns:
            [SystemHostObject]: List of computes objects
        """
        system_host_output = self.get_system_host_with_extra_column(["capabilities"])
        computes = system_host_output.get_computes()

        return computes

    def get_storages(self) -> [SystemHostObject]:
        """
        Gets the storages

        Returns:
            [SystemHostObject]: List of storage objects
        """
        system_host_output = self.get_system_host_with_extra_column(["capabilities"])
        storages = system_host_output.get_storages()

        return storages

    def get_workers(self) -> [SystemHostObject]:
        """
        Gets hosts with worker subfunction

        Returns:
            [SystemHostObject]: List of hosts with worker capability
        """
        system_host_output = self.get_system_host_with_extra_column(["subfunctions"])
        workers = system_host_output.get_workers()

        return workers

    def get_uptime(self, host_name: str) -> int:
        """
        Gets the uptime of the given host

        Args:
            host_name(str): the name of the host

        Returns:
            int: the uptime in secs
        """
        system_host_output = self.get_system_host_with_extra_column(["uptime"])
        uptime = system_host_output.get_host(host_name).get_uptime()

        return uptime

    def wait_for_host_availability(self, host_name: str, target_states: List[str], timeout: int = 600, polling_sleep_time: int = 15) -> None:
        """Wait for a host to reach one of the target availability states.

        Polls 'system host-list' until the named host reports an availability
        value contained in target_states, failing on timeout so the wait points
        at the failure on the spot rather than returning a value the caller must
        remember to assert on.

        Args:
            host_name (str): the name of the host to poll
            target_states (List[str]): acceptable availability values (e.g. ["available"])
            timeout (int): maximum number of seconds to wait
            polling_sleep_time (int): number of seconds to sleep between polls

        Raises:
            TimeoutError: if the host does not reach one of the target states
                within the timeout.
        """

        def get_availability() -> str:
            availability = self.get_system_host_list().get_host(host_name).get_availability()
            get_logger().log_info(f"Host '{host_name}' availability is '{availability}', waiting for one of {target_states}")
            return availability

        validate_list_contains_with_retry(get_availability, target_states, f"Host '{host_name}' reached one of availability states {target_states}", timeout=timeout, polling_sleep_time=polling_sleep_time)

    def get_system_host_with_extra_column(self, columns_to_add: [str]) -> SystemHostOutput:
        """
        Gets the system host list with extra columns

        Args:
            columns_to_add ([str]): list os columns to add in the system host list command output
        Returns:
            SystemHostOutput: object represents the system host-list command output
        """
        cmd = f"system host-list --column id --column hostname --column personality --column operational --column availability --column administrative {' '.join(['--column ' + column_to_add for column_to_add in columns_to_add])} --nowrap"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        system_host_output = SystemHostOutput(output)

        return system_host_output
