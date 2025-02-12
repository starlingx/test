from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.load.objects.system_load_object import SystemLoadObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemLoadShowOutput:
    """
    This class parses the output of 'system load-show' command into an object of type SystemLoadShowObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system load-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_load = SystemLoadObject()
            self.system_load.set_id(output_values['id'])
            self.system_load.set_state(output_values['state'])
            self.system_load.set_software_version(output_values['software_version'])
            self.system_load.set_compatible_version(output_values['compatible_version'])
            self.system_load.set_required_patches(output_values['required_patches'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_load_show(self) -> SystemLoadObject:
        """
        Returns the parsed system load-show object.

        Returns:
        SystemLoadObject: The parsed system load-show object.
        """

        return self.system_load

    @staticmethod
    def is_valid_output(value) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["id", "state", "software_version", "compatible_version", "required_patches"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid