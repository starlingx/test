from framework.ssh.ssh_connection import SSHConnection
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
