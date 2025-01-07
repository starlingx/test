from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_disk_partition_output import SystemHostDiskPartitionOutput
from keywords.cloud_platform.system.host.objects.system_host_disk_partition_show_output import SystemHostDiskPartitionShowOutput


class SystemHostDiskPartitionKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-disk-partition' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_disk_partition_list(self, host_id) -> SystemHostDiskPartitionOutput:
        """
        Gets the system host-disk-partition-list

        Args:
            host_id: name or id of the host
        Returns:
            SystemHostDiskPartitionOutput object with the list of disk-partition.

        """
        command = source_openrc(f'system host-disk-partition-list {host_id}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_disk_part_output = SystemHostDiskPartitionOutput(output)
        return system_host_disk_part_output

    def get_system_host_disk_partition_show(self, host_id, uuid) -> SystemHostDiskPartitionShowOutput:
        """
        Gets the system host-disk-partition-show

        Args:
            host_id: name or id of the host
            uuid: uuid of partition
        Returns:
            SystemHostDiskPartitionShowOutput object.

        """
        command = source_openrc(f'system host-disk-partition-show {host_id} {uuid}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_disk_partition_output = SystemHostDiskPartitionShowOutput(output)
        return system_host_disk_partition_output