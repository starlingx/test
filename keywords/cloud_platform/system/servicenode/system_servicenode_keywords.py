from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.servicenode.objects.system_servicenode_output import SystemServicenodeOutput
from keywords.cloud_platform.system.servicenode.objects.system_servicenode_show_output import SystemServicenodeShowOutput


class SystemServicenodeKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system servicenode' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_servicenode_list(self) -> SystemServicenodeOutput:
        """
        Gets the system servicenode-list

        Args:

        Returns:
            SystemServicenodeOutput object with the list of servicenode.

        """
        command = source_openrc(f'system servicenode-list')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_servicenode_output = SystemServicenodeOutput(output)
        return system_servicenode_output

    def get_system_servicenode_show(self, host_id) -> SystemServicenodeShowOutput:
        """
        Gets the system servicenode-show

        Args:
            host_id: host id

        Returns:
            SystemServicenodeShowOutput object.

        """
        command = source_openrc(f'system servicenode-show {host_id}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_servicenode_show_output = SystemServicenodeShowOutput(output)
        return system_servicenode_show_output