from typing import Optional

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_object import SystemServiceParameterListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemServiceParameterListOutput:
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
        self.parameters = []
        self.log = get_logger()

        if self.is_valid_output(self.output):
            # Convert Property/Value pairs to a single parameter object
            for line in output_values_list:
                # One param for line
                param = SystemServiceParameterListObject()
                for item in line.items():
                    property_name, property_value = item
                    if property_name == "uuid":
                        param.set_uuid(property_value)
                    elif property_name == "service":
                        param.set_service(property_value)
                    elif property_name == "section":
                        param.set_section(property_value)
                    elif property_name == "name":
                        param.set_name(property_value)
                    elif property_name == "value":
                        param.set_value(property_value)
                self.parameters.append(param)
        else:
            raise KeywordException(f"The output {self.output} was not valid")

    def get_parameters(self) -> list:
        """
        Get list of service parameter objects.

        Returns:
            list: List of SystemServiceParameterObject instances
        """
        return self.parameters

    def get_parameter_by_name(self, name: str) -> Optional[SystemServiceParameterListObject]:
        """
        Get parameter by name.

        Args:
            name (str): Parameter name to search for
        Returns:
            Optional[SystemServiceParameterListObject]: Parameter object if found, None otherwise
        """
        for param in self.parameters:
            if param.get_name() == name:
                return param
        return None

    def get_docker_registry_url(self) -> str:
        """
        Get the docker registry URL from service parameters.

        Returns:
            str: Docker registry URL or None if not found
        """
        for param in self.parameters:
            if param.get_section() == "docker-registry" and param.get_name() == "url":
                return param.get_value()
        return None

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

        # Empty output (just whitespace/newlines) is valid for empty sections
        if not output_str.strip():
            return True

        # If there's content, it should have proper table structure
        if "uuid" not in output_str or "value" not in output_str:
            get_logger().log.log_error("Required uuid/value table structure not found in output")
            return False

        return True
