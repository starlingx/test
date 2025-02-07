from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.service.objects.system_service_object import SystemServiceObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemServiceOutput:
    """
    This class parses the output of 'system service-list' command into an object of type SystemServiceObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system service-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_services : [SystemServiceObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_service = SystemServiceObject()
                system_service.set_id(value['id'])
                system_service.set_service_name(value['service_name'])
                system_service.set_hostname(value['hostname'])
                system_service.set_state(value['state'])
                self.system_services.append(system_service)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_service_list(self) -> list[SystemServiceObject]:
        """
        Returns the parsed system service object.

        Returns:
        list[SystemServiceObject]: list of parsed system service objects.
        """

        return self.system_services

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
