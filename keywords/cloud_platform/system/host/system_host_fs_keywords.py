from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_fs_output import SystemHostFSOutput


class SystemHostFSKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-fs-list' command.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_fs_list(self, host_name) -> SystemHostFSOutput:
        """
        Gets the system host-fs-list <host_name>

        Returns:
            SystemHostFSOutput object with the list of hostfs.

        """
        command = source_openrc(f'system host-fs-list {host_name}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_fs_output = SystemHostFSOutput(output)
        return system_host_fs_output


