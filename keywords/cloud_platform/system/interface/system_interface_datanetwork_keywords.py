from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.interface.objects.system_interface_datanetwork_output import SystemInterfaceDatanetworkOutput


class SystemInterfaceDatanetworkKeywords(BaseKeyword):
    """
    Class for system interface-datanetwork keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def interface_datanetwork_list(self, host_name: str) -> SystemInterfaceDatanetworkOutput:
        """
        Keyword for system interface-datanetwork-list
        Args:
            host_name (): the name of the host

        Returns:SystemInterfaceDatanetowrkOutput

        """
        output = self.ssh_connection.send(source_openrc(f'system interface-datanetwork-list --nowrap {host_name}'))
        self.validate_success_return_code(self.ssh_connection)
        system_interface_network_if_output = SystemInterfaceDatanetworkOutput(output)
        return system_interface_network_if_output

    def interface_datanetwork_assign(self, hostname: str, interface_name: str, datanetwork_name: str):
        """
        Keyword to assign interface to a datanetwork
        Args:
            hostname (): the hostname
            interface_name (): the interface name
            datanetwork_name (): the datanetwork name

        Returns:

        """
        self.ssh_connection.send(source_openrc(f'system interface-datanetwork-assign {hostname} {interface_name} {datanetwork_name}'))
        self.validate_success_return_code(self.ssh_connection)
