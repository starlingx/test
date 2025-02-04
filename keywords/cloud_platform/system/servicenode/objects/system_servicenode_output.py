from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.servicenode.objects.system_servicenode_object import SystemServicenodeObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemServicenodeOutput:
    """
    This class parses the output of 'system servicenode-list' command into an object of type SystemServicenodeObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system servicenode-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_servicenodes : [SystemServicenodeObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_servicenode = SystemServicenodeObject()
                system_servicenode.set_id(value['id'])
                system_servicenode.set_name(value['name'])
                system_servicenode.set_administrative(value['administrative'])
                system_servicenode.set_operational(value['operational'])
                system_servicenode.set_availability(value['availability'])
                system_servicenode.set_ready_state(value['ready_state'])
                self.system_servicenodes.append(system_servicenode)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_servicenode_list(self) -> list[SystemServicenodeObject]:
        """
        Returns the parsed system servicenode object.

        Returns:
        list[SystemServicenodeObject]: list of parsed system servicenode objects.
        """

        return self.system_servicenodes

    @staticmethod
    def is_valid_output(value) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["id", "name", "administrative", "operational", "availability", "ready_state"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
