from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.network.objects.system_network_output import SystemNetworkOutput
from keywords.cloud_platform.system.network.objects.system_network_show_output import SystemNetworkShowOutput


class SystemNetworkKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system network' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_network_list(self) -> SystemNetworkOutput:
        """
        Gets the system network-list

        Returns:
            SystemNetworkOutput object with the list of network.

        """
        command = source_openrc('system network-list')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_network_output = SystemNetworkOutput(output)
        return system_network_output

    def get_system_network_show(self, network_uuid) -> SystemNetworkShowOutput:
        """
        Gets the system network-list

        Args:
            network_uuid of the network

        Returns:
            SystemNetworkShowOutput object with the list of network.

        """
        command = source_openrc(f'system network-show {network_uuid}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_network_output = SystemNetworkShowOutput(output)
        return system_network_output
