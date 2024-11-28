from keywords.cloud_platform.system.host.objects.system_host_disk_object import SystemHostDiskObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostDiskOutput:
    """
    This class parses the output of 'system host-disk-list' commands into a list of SystemHostDiskObject
    """

    def __init__(self, system_host_disk_output):
        """
        Constructor

        Args:
            system_host_disk_output: String output of 'system host-disk-list' command
        """

        self.system_host_disks: [SystemHostDiskObject] = []
        system_table_parser = SystemTableParser(system_host_disk_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:

            system_host_disk_object = SystemHostDiskObject()

            if 'uuid' in value:
                system_host_disk_object.set_uuid(value['uuid'])

            if 'device_node' in value:
                system_host_disk_object.set_device_node(value['device_node'])

            if 'device_num' in value:
                system_host_disk_object.set_device_num(value['device_num'])

            if 'device_type' in value:
                system_host_disk_object.set_device_type(value['device_type'])

            if 'size_gib' in value:
                system_host_disk_object.set_size_gib(float(value['size_gib']))

            if 'available_gib' in value:
                system_host_disk_object.set_available_gib(float(value['available_gib']))

            if 'rpm' in value:
                system_host_disk_object.set_rpm(value['rpm'])

            if 'serial_id' in value:
                system_host_disk_object.set_serial_id(value['serial_id'])

            if 'device_path' in value:
                system_host_disk_object.set_device_path(value['device_path'])

            self.system_host_disks.append(system_host_disk_object)

    def has_minimum_disk_space_in_gb(self, minimum_disk_space_in_gb: float) -> bool:
        """
        This function will look for a disk in the list of disks with at least <minimum_disk_space_in_gb> GB
        of free space.

        Returns: True if this host has at least one disk with at least <minimum_disk_space_in_gb> GB of free space.

        """
        return any(item.get_available_gib() >= minimum_disk_space_in_gb for item in self.system_host_disks)
