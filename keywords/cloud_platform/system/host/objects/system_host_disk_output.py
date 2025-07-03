from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.system_host_disk_object import SystemHostDiskObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostDiskOutput:
    """Parses the output of 'system host-disk-list' commands into SystemHostDiskObject instances."""

    def __init__(self, system_host_disk_output: str | RestResponse) -> None:
        """Initialize SystemHostDiskOutput with parsed disk data.

        Args:
            system_host_disk_output (str | RestResponse): String output from 'system host-disk-list' command or RestResponse object.
        """
        self.system_host_disks: list[SystemHostDiskObject] = []

        if isinstance(system_host_disk_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_disk_output.get_json_content()
            if "idisks" in json_object:
                disks = json_object["idisks"]
            else:
                disks = [json_object]
        else:
            system_table_parser = SystemTableParser(system_host_disk_output)
            disks = system_table_parser.get_output_values_list()

        for value in disks:

            system_host_disk_object = SystemHostDiskObject()

            if "uuid" in value:
                system_host_disk_object.set_uuid(value["uuid"])

            if "device_node" in value:
                system_host_disk_object.set_device_node(value["device_node"])

            if "device_num" in value:
                system_host_disk_object.set_device_num(value["device_num"])

            if "device_type" in value:
                system_host_disk_object.set_device_type(value["device_type"])

            if "size_gib" in value:
                system_host_disk_object.set_size_gib(float(value["size_gib"]))
            if "size_mib" in value:
                system_host_disk_object.set_size_gib(float(value["size_mib"]) / 1024.0)

            if "available_gib" in value:
                system_host_disk_object.set_available_gib(float(value["available_gib"]))

            if "available_mib" in value:
                system_host_disk_object.set_available_gib(float(value["available_mib"]) / 1024.0)

            if "rpm" in value:
                system_host_disk_object.set_rpm(value["rpm"])

            if "serial_id" in value:
                system_host_disk_object.set_serial_id(value["serial_id"])

            if "device_path" in value:
                system_host_disk_object.set_device_path(value["device_path"])

            self.system_host_disks.append(system_host_disk_object)

    def has_minimum_disk_space_in_gb(self, minimum_disk_space_in_gb: float) -> bool:
        """Check if any disk has at least the specified amount of free space.

        Args:
            minimum_disk_space_in_gb (float): The minimum required free disk space in GB.

        Returns:
            bool: True if at least one disk has the minimum required free space, False otherwise.
        """
        return any(item.get_available_gib() >= minimum_disk_space_in_gb for item in self.system_host_disks)
