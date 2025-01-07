from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_disk_partition_object import SystemHostDiskPartitionObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemHostDiskPartitionShowOutput:
    """
    This class parses the output of 'system host-disk-partition-show' command into an object of type SystemHostDiskPartitionObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system host-disk-partition-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_host_disk_partition = SystemHostDiskPartitionObject()
            self.system_host_disk_partition.set_device_path(output_values['device_path'])
            self.system_host_disk_partition.set_device_node(output_values['device_node'])
            self.system_host_disk_partition.set_type_guid(output_values['type_guid'])
            self.system_host_disk_partition.set_type_name(output_values['type_name'])
            self.system_host_disk_partition.set_start_mib(output_values['start_mib'])
            self.system_host_disk_partition.set_end_mib(output_values['end_mib'])
            self.system_host_disk_partition.set_size_mib(output_values['size_mib'])
            self.system_host_disk_partition.set_uuid(output_values['uuid'])
            self.system_host_disk_partition.set_ihost_uuid(output_values['ihost_uuid'])
            self.system_host_disk_partition.set_idisk_uuid(output_values['idisk_uuid'])
            self.system_host_disk_partition.set_ipv_uuid(output_values['ipv_uuid'])
            self.system_host_disk_partition.set_status(output_values['status'])
            self.system_host_disk_partition.set_created_at(output_values['created_at'])
            self.system_host_disk_partition.set_updated_at(output_values['updated_at'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_host_disk_partition_show(self):
        """
        Returns the parsed system host-disk-partition object.

        Returns:
        SystemHostAddrObject: The parsed system host-disk-partition object.
        """

        return self.system_host_disk_partition

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "device_path", "device_node", "type_guid", "type_name",
                           "size_mib", "start_mib", "end_mib", "status","ihost_uuid",
                           "idisk_uuid", "ipv_uuid", "created_at", "updated_at"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
