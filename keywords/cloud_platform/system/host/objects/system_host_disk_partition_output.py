from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_disk_partition_object import SystemHostDiskPartitionObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemHostDiskPartitionOutput:
    """
    This class parses the output of 'system host-disk-partition-list' command into an object of type SystemHostDiskPartitionObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system host-disk-partition-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_host_disk_part : [SystemHostDiskPartitionObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_host_disk_part = SystemHostDiskPartitionObject()
                system_host_disk_part.set_uuid(value['uuid'])
                system_host_disk_part.set_device_path(value['device_path'])
                system_host_disk_part.set_device_node(value['device_node'])
                system_host_disk_part.set_type_guid(value['type_guid'])
                system_host_disk_part.set_type_name(value['type_name'])
                system_host_disk_part.set_size_gib(value['size_gib'])
                system_host_disk_part.set_status(value['status'])
                self.system_host_disk_part.append(system_host_disk_part)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_host_disk_partition(self):
        """
        Returns the parsed system host-disk-partition object.

        Returns:
        SystemHostDiskPartitionObject: The parsed system host-disk-partition object.
        """

        return self.system_host_disk_part

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "device_path", "device_node", "type_guid", "type_name", "size_gib", "status"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
