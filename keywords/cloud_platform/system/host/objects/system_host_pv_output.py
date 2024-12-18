from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_pv_object import SystemHostPvObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemHostPvOutput:
    """
    This class parses the output of 'system host-pv-list' command into an object of type SystemHostLvgObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system host-pv-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_host_pv : [SystemHostPvObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_host_pv = SystemHostPvObject()
                system_host_pv.set_uuid(value['uuid'])
                system_host_pv.set_lvm_pv_name(value['lvm_pv_name'])
                system_host_pv.set_disk_or_part_uuid(value['disk_or_part_uuid'])
                system_host_pv.set_disk_or_part_device_node(value['disk_or_part_device_node'])
                system_host_pv.set_disk_or_part_device_path(value['disk_or_part_device_path'])
                system_host_pv.set_pv_state(value['pv_state'])
                system_host_pv.set_pv_type(value['pv_type'])
                system_host_pv.set_lvm_vg_name(value['lvm_vg_name'])
                system_host_pv.set_ihost_uuid(value['ihost_uuid'])
                self.system_host_pv.append(system_host_pv)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_host_pv(self):
        """
        Returns the parsed system host-pv object.

        Returns:
        SystemHostAddrObject: The parsed system host-pv object.
        """

        return self.system_host_pv

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "lvm_pv_name", "disk_or_part_uuid", "disk_or_part_device_node", "disk_or_part_device_path",
                           "pv_state", "pv_type", "lvm_vg_name", "ihost_uuid"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
