from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_port_output import SystemHostPortOutput


class SystemHostPortKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-port-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_port_list(self, hostname) -> SystemHostPortOutput:
        """
        Gets the system host port list

        Args:
            hostname: Name of the host for which we want to get the port list.

        Returns: SystemHostPortOutput

        """
        output = self.ssh_connection.send(source_openrc(f'system host-port-list --nowrap {hostname}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_port_output = SystemHostPortOutput(output)

        return system_host_port_output
