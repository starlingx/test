from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_addr_object import SystemHostAddrObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemHostAddrShowOutput:
    """
    This class parses the output of 'system host-addr-show' command into an object of type SystemHostAddrObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system host-addr-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_host_addr_object = SystemHostAddrObject()
            self.system_host_addr_object.set_uuid(output_values['uuid'])
            self.system_host_addr_object.set_interface_uuid(output_values['interface_uuid'])
            self.system_host_addr_object.set_if_name(output_values['ifname'])
            self.system_host_addr_object.set_forihostid(output_values['forihostid'])
            self.system_host_addr_object.set_address(output_values['address'])
            self.system_host_addr_object.set_prefix(output_values['prefix'])
            self.system_host_addr_object.set_enable_dad(output_values['enable_dad'])
            self.system_host_addr_object.set_pool_uuid(output_values['pool_uuid'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_host_addr_show(self):
        """
        Returns the parsed system host-addr object.

        Returns:
        SystemHostAddrObject: The parsed system host-addr object.
        """

        return self.system_host_addr_object

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "interface_uuid", "ifname", "forihostid", "address", "prefix",
                           "enable_dad", "pool_uuid"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
