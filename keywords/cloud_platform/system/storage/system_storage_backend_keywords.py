from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.storage.objects.system_storage_backend_output import SystemStorageBackendOutput


class SystemStorageBackendKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system storage-backend-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_storage_backend_list(self) -> SystemStorageBackendOutput:
        """
        Gets the system backend list

        Returns:

        """
        output = self.ssh_connection.send(source_openrc('system storage-backend-list --nowrap'))
        self.validate_success_return_code(self.ssh_connection)
        system_storage_backend_output = SystemStorageBackendOutput(output)

        return system_storage_backend_output