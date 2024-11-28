from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.network.objects.system_network_object import SystemNetworkObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemNetworkOutput:
    """
    This class parses the output of 'system network-list' command into an object of type SystemNetwork.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system network-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_network : [SystemNetworkObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_network = SystemNetworkObject()
                system_network.set_id(value['id'])
                system_network.set_uuid(value['uuid'])
                system_network.set_name(value['name'])
                system_network.set_type(value['type'])
                system_network.set_dynamic(value['dynamic'])
                system_network.set_pool_uuid(value['pool_uuid'])
                system_network.set_primary_pool_family(value['primary_pool_family'])
                self.system_network.append(system_network)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_network(self):
        """
        Returns the parsed network object.

        Returns:
        SystemNetworkObject: The parsed network object.
        """

        return self.system_network

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
