from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.servicenode.objects.system_servicenode_object import SystemServicenodeObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemServicenodeShowOutput:
    """
    This class parses the output of 'system servicenode-show' command into an object of type SystemServicenodeObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system servicenode-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_servicenode = SystemServicenodeObject()
            self.system_servicenode.set_administrative_state(output_values['administrative_state'])
            self.system_servicenode.set_availability_status(output_values['availability_status'])
            self.system_servicenode.set_id(output_values['id'])
            self.system_servicenode.set_name(output_values['name'])
            self.system_servicenode.set_operational_state(output_values['operational_state'])
            self.system_servicenode.set_ready_state(output_values['ready_state'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_servicenode_show(self) -> SystemServicenodeObject:
        """
        Returns the parsed system servicenode-show object.

        Returns:
        SystemServicenodeObject: The parsed system servicenode-show object.
        """

        return self.system_servicenode

    @staticmethod
    def is_valid_output(value) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["administrative_state", "availability_status", "id", "name", "operational_state", "ready_state"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
