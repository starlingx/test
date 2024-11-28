from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_show_output import SystemHostShowOutput


class SystemHostShowKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-show-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_show_output(self, hostname) -> SystemHostShowOutput:
        """
        Gets the system host cpu list

        Args:
            hostname: Name of the host for which we want to get the cpu list.

        Returns:

        """
        output = self.ssh_connection.send(source_openrc(f'system host-show {hostname}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_show_output = SystemHostShowOutput(output)

        return system_host_show_output
