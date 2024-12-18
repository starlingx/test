from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_pv_object import SystemHostPvObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemHostPvShowOutput:
    """
    This class parses the output of 'system host-pv-show' command into an object of type SystemHostPvObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system host-pv-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_host_pv = SystemHostPvObject()
            self.system_host_pv.set_uuid(output_values['uuid'])
            self.system_host_pv.set_pv_state(output_values['pv_state'])
            self.system_host_pv.set_pv_type(output_values['pv_type'])
            self.system_host_pv.set_disk_or_part_uuid(output_values['disk_or_part_uuid'])
            self.system_host_pv.set_disk_or_part_device_node(output_values['disk_or_part_device_node'])
            self.system_host_pv.set_disk_or_part_device_path(output_values['disk_or_part_device_path'])
            self.system_host_pv.set_lvm_pv_name(output_values['lvm_pv_name'])
            self.system_host_pv.set_lvm_vg_name(output_values['lvm_vg_name'])
            self.system_host_pv.set_lvm_pv_uuid(output_values['lvm_pv_uuid'])
            self.system_host_pv.set_lvm_pv_size_gib(output_values['lvm_pv_size_gib'])
            self.system_host_pv.set_lvm_pe_total(output_values['lvm_pe_total'])
            self.system_host_pv.set_lvm_pe_alloced(output_values['lvm_pe_alloced'])
            self.system_host_pv.set_ihost_uuid(output_values['ihost_uuid'])
            self.system_host_pv.set_created_at(output_values['created_at'])
            self.system_host_pv.set_updated_at(output_values['updated_at'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_host_pv_show(self):
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

        required_fields = ["uuid", "pv_state", "pv_type", "disk_or_part_uuid", "disk_or_part_device_node", "disk_or_part_device_path",
                           "lvm_pv_name", "lvm_vg_name", "lvm_pv_uuid", "lvm_pv_size_gib", "lvm_pe_total",
                           "lvm_pe_alloced", "ihost_uuid", "created_at", "updated_at"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
