from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_addr_output import SystemHostAddrOutput
from keywords.cloud_platform.system.host.objects.system_host_addr_show_output import SystemHostAddrShowOutput

class SystemHostAddrKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-addr' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_addr_list(self, hostname) -> SystemHostAddrOutput:
        """
        Gets the system host-addr-list

        Args:
            hostname: name or id of the host
        Returns:
            SystemHostAddrOutput object with the list of host-addr.

        """
        command = source_openrc(f'system host-addr-list {hostname}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_addr_output = SystemHostAddrOutput(output)
        return system_host_addr_output

    def get_system_host_addr_show(self, uuid) -> SystemHostAddrShowOutput:
        """
        Gets the system host-addr-show

        Args:
            uuid: uuid of the host addr
        Returns:
            SystemHostAddrShowOutput object.

        """
        command = source_openrc(f'system host-addr-show {uuid}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_addr_output = SystemHostAddrShowOutput(output)
        return system_host_addr_output
