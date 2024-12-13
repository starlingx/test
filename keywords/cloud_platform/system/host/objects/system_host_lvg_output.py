from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_lvg_object import SystemHostLvgObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemHostLvgOutput:
    """
    This class parses the output of 'system host-lvg-list' command into an object of type SystemHostLvgObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system host-lvg-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_host_lvg : [SystemHostLvgObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_host_lvg = SystemHostLvgObject()
                system_host_lvg.set_uuid(value['UUID'])
                system_host_lvg.set_lvg_name(value['LVG Name'])
                system_host_lvg.set_state(value['State'])
                system_host_lvg.set_access(value['Access'])
                system_host_lvg.set_total_size(value['Total Size (GiB)'])
                system_host_lvg.set_avail_size(value['Avail Size (GiB)'])
                system_host_lvg.set_current_pvs(value['Current PVs'])
                system_host_lvg.set_current_lvs(value['Current LVs'])
                self.system_host_lvg.append(system_host_lvg)
            else:
                raise KeywordException(f"The output line {value} was not valid")

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

        required_fields = ["UUID", "LVG Name", "State", "Access", "Total Size (GiB)", "Avail Size (GiB)",
                           "Current PVs", "Current LVs"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
