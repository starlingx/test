from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_memory_output import SystemHostMemoryOutput


class SystemHostMemoryKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-memory-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_memory_list(self, hostname) -> SystemHostMemoryOutput:
        """
        Gets the system host memory list

        Args:
            hostname: Name of the host for which we want to get the memory list.

        Returns:

        """
        output = self.ssh_connection.send(source_openrc(f'system host-memory-list --nowrap {hostname}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_cpu_output = SystemHostMemoryOutput(output)

        return system_host_cpu_output
