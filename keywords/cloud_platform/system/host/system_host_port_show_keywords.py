from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_port_show_output import SystemHostPortShowOutput


class SystemHostPortShowKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-port-show <controller-id/hostname> <interface/uuid>' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_port_show(self, hostname, interface_name) -> SystemHostPortShowOutput:
        """
        Gets the system host port show

        Args:
            hostname: Name of the host for which we want to get the port show.
            interface_name: Name of the interface for which we want to get the port show

        Returns: SystemHostPortOutput

        """
        output = self.ssh_connection.send(source_openrc(f'system host-port-show {hostname} {interface_name}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_port_output = SystemHostPortShowOutput(output)

        return system_host_port_output
