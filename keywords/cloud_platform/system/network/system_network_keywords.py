from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.network.objects.system_network_output import SystemNetworkOutput

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


