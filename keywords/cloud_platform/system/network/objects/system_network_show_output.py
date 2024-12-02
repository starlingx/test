from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.network.objects.system_network_object import SystemNetworkObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemNetworkShowOutput:
    """
    This class parses the output of 'system network-show' command into an object of type SystemNetworkObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output: output of 'system network-show' command.
        """
        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_network_show_object = SystemNetworkObject()
            self.system_network_show_object.set_id(output_values['id'])
            self.system_network_show_object.set_uuid(output_values['uuid'])
            self.system_network_show_object.set_name(output_values['name'])
            self.system_network_show_object.set_type(output_values['type'])
            self.system_network_show_object.set_dynamic(output_values['dynamic'])
            self.system_network_show_object.set_pool_uuid(output_values['pool_uuid'])
            self.system_network_show_object.set_primary_pool_family(output_values['primary_pool_family'])
        else:
                raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_network_show(self):
        """
        Returns the parsed network object.

        Returns:
        SystemNetworkObject: The parsed network object.
        """

        return self.system_network_show_object

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["id", "uuid", "name", "type", "dynamic", "pool_uuid", "primary_pool_family"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
