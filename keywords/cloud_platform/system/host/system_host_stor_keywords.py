from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_stor_output import SystemHostStorageOutput


class SystemHostStorageKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-stor-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_stor_list(self, hostname) -> SystemHostStorageOutput:
        """
        Gets the system host storage list

        Args:
            hostname: Name of the host for which we want to get the storage list.

        Returns:
            SystemHostStorageOutput object with the list of storages of this host.

        """
        output = self.ssh_connection.send(source_openrc(f'system host-stor-list --nowrap {hostname}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_storage_output = SystemHostStorageOutput(output)

        return system_host_storage_output
