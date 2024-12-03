from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_addr_object import SystemHostAddrObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemHostAddrOutput:
    """
    This class parses the output of 'system host-addr-list' command into an object of type SystemHostAddrObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system host-addr-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_host_addr : [SystemHostAddrObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_host_addr = SystemHostAddrObject()
                system_host_addr.set_uuid(value['uuid'])
                system_host_addr.set_if_name(value['ifname'])
                system_host_addr.set_address(value['address'])
                system_host_addr.set_prefix(value['prefix'])
                self.system_host_addr.append(system_host_addr)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_host_addr(self):
        """
        Returns the parsed system host-addr object.

        Returns:
        SystemHostAddrObject: The parsed system host-addr object.
        """

        return self.system_host_addr

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "ifname", "address", "prefix"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
