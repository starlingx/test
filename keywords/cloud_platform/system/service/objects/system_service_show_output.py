from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.service.objects.system_service_object import SystemServiceObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemServiceShowOutput:
    """
    This class parses the output of 'system service-show' command into an object of type SystemServiceObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system service-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_service = SystemServiceObject()
            self.system_service.set_id(output_values['id'])
            self.system_service.set_service_name(output_values['service_name'])
            self.system_service.set_hostname(output_values['hostname'])
            self.system_service.set_state(output_values['state'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_service_show(self) -> SystemServiceObject:
        """
        Returns the parsed system service-show object.

        Returns:
        SystemServiceObject: The parsed system service-show object.
        """

        return self.system_service

    @staticmethod
    def is_valid_output(value) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["id", "service_name", "hostname", "state"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
