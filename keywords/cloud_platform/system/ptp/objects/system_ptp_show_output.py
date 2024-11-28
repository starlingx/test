from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.ptp.objects.system_ptp_object import SystemPTPObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemPTPShowOutput:
    """
    This class parses the output of 'system ptp-show' command into an object of type SystemPTPShowObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system ptp-show' command.

        Raises:
            KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_ptp_show_object = SystemPTPObject(
                output_values['uuid'],
                output_values['mode'],
                output_values['transport'],
                output_values['mechanism'],
                output_values['isystem_uuid'],
            )
            if 'created_at' in output_values:
                self.system_ptp_show_object.set_created_at(output_values['created_at'])
            if 'updated_at' in output_values:
                self.system_ptp_show_object.set_updated_at(output_values['updated_at'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_ptp_object(self) -> SystemPTPObject:
        """
        Returns the parsed ptp object.

        Returns:
            SystemPTPObject: The parsed ptp object.
        """
        return self.system_ptp_show_object

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        valid = True
        required_fields = ['uuid', 'mode', 'transport', 'mechanism', 'isystem_uuid', 'created_at', 'updated_at']

        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value: {value}')
                valid = False
        return valid