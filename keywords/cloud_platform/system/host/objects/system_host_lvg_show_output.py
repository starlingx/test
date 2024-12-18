from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_lvg_object import SystemHostLvgObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemHostLvgShowOutput:
    """
    This class parses the output of 'system host-lvg-show' command into an object of type SystemHostLvgObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system host-lvg-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_host_lvg = SystemHostLvgObject()
            self.system_host_lvg.set_uuid(output_values['uuid'])
            self.system_host_lvg.set_lvg_name(output_values['lvm_vg_name'])
            self.system_host_lvg.set_state(output_values['vg_state'])
            self.system_host_lvg.set_ihost_uuid(output_values['ihost_uuid'])
            self.system_host_lvg.set_access(output_values['lvm_vg_access'])
            self.system_host_lvg.set_lvm_max_lv(output_values['lvm_max_lv'])
            self.system_host_lvg.set_current_lvs(output_values['lvm_cur_lv'])
            self.system_host_lvg.set_lvm_max_pv(output_values['lvm_max_pv'])
            self.system_host_lvg.set_current_pvs(output_values['lvm_cur_pv'])
            self.system_host_lvg.set_total_size(output_values['lvm_vg_size_gib'])
            self.system_host_lvg.set_avail_size(output_values['lvm_vg_avail_size_gib'])
            self.system_host_lvg.set_lvm_vg_total_pe(output_values['lvm_vg_total_pe'])
            self.system_host_lvg.set_lvm_vg_free_pe(output_values['lvm_vg_free_pe'])
            self.system_host_lvg.set_created_at(output_values['created_at'])
            self.system_host_lvg.set_updated_at(output_values['updated_at'])
            self.system_host_lvg.set_parameters(output_values['parameters'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_host_lvg(self):
        """
        Returns the parsed system host-lvg object.

        Returns:
        SystemHostAddrObject: The parsed system host-lvg object.
        """

        return self.system_host_lvg

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["lvm_vg_name", "vg_state", "uuid", "ihost_uuid", "lvm_vg_access", "lvm_max_lv",
                           "lvm_cur_lv", "lvm_max_pv", "lvm_cur_pv", "lvm_vg_size_gib", "lvm_vg_avail_size_gib",
                           "lvm_vg_total_pe", "lvm_vg_free_pe", "created_at", "updated_at", "parameters"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
