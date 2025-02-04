from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.storage.objects.system_storage_tier_output import SystemStorageTierOutput
from keywords.cloud_platform.system.storage.objects.system_storage_tier_show_output import SystemStorageTierShowOutput


class SystemStorageTierKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system storage-tier' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_storage_tier_list(self, cluster_uuid) -> SystemStorageTierOutput:
        """
        Gets the system storage-tier-list

        Args:

        Returns:
            SystemStorageTierOutput object with the list of storage-tier.

        """
        command = source_openrc(f'system storage-tier-list {cluster_uuid}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_sto_tier_output = SystemStorageTierOutput(output)
        return system_sto_tier_output

    def get_system_storage_tier_show(self, cluster_uuid, tier_uuid) -> SystemStorageTierShowOutput:
        """
        Gets the system storage-tier-show

        Args:
            cluster_uuid: name or uuid of the cluster
            tier_uuid: uuid of the storage tier

        Returns:
            SystemStorageTierShowOutput object.

        """
        command = source_openrc(f'system storage-tier-show {cluster_uuid} {tier_uuid}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_sto_tier_show_output = SystemStorageTierShowOutput(output)
        return system_sto_tier_show_output