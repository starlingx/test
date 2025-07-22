from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemServiceParameterOutput:
    """
    Class to parse and handle the output of 'system service-parameter-list' command.
    """

    def __init__(self, output: str):
        """
        Constructor.

        Args:
            output (str): Raw output from 'system service-parameter-list' command

        Raises:
            KeywordException: If the output is not valid
        """
        self.output = output.split("\n") if isinstance(output, str) else output
        self.table_parser = SystemTableParser(self.output)
        output_values_list = self.table_parser.get_output_values_list()

        if self.is_valid_output(self.output):
            # Convert Property/Value pairs to a single parameter object
            param = SystemServiceParameterObject()
            for item in output_values_list:
                property_name = item.get("Property", "")
                property_value = item.get("Value", "")

                if property_name == "service":
                    param.set_service(property_value)
                elif property_name == "section":
                    param.set_section(property_value)
                elif property_name == "name":
                    param.set_name(property_value)
                elif property_name == "value":
                    param.set_value(property_value)

            self.parameters = [param]
        else:
            raise KeywordException(f"The output {self.output} was not valid")

    def get_parameters(self) -> list:
        """
        Get list of service parameter objects.

        Returns:
            list: List of SystemServiceParameterObject instances
        """
        return self.parameters

    def get_raw_output(self) -> str:
        """
        Get the raw output from the command.

        Returns:
            str: Raw command output
        """
        return self.output

    @staticmethod
    def is_valid_output(output: list) -> bool:
        """
        Checks if the output contains valid service parameter data.

        Args:
            output (list): The command output to validate

        Returns:
            bool: True if the output is valid, False otherwise
        """
        output_str = "\n".join(output) if isinstance(output, list) else output

        # Check for Property/Value table structure
        if "Property" not in output_str or "Value" not in output_str:
            get_logger().log_error("Required Property/Value table structure not found in output")
            return False

        return True
