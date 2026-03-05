from typing import Union

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemServiceParameterListOutput:
    """Parses and handles the output of 'system service-parameter-list' command.

    Args:
        output (Union[str, list]): Output of 'system service-parameter-list'
                                   command

    Raises:
        KeywordException: If the output is not valid

    Sample Output:
    +--------------------------------------+----------+---------+--------------------+-------+-------------+----------+
    | uuid                                 | service  | section | name               | value | personality | resource |
    +--------------------------------------+----------+---------+--------------------+-------+-------------+----------+
    | c3e8706f-ab09-4327-ad61-4d0c6e602ed3 | platform | sysctl  | kernel.panic_print | 0     | None        | None     |
    | cb5733ce-4bac-4caa-a85d-918ecb78aa75 | platform | sysctl  | vm.swappiness      | 10    | None        | None     |
    +--------------------------------------+----------+---------+--------------------+-------+-------------+----------+

    """

    def __init__(self, output: Union[str, list]):

        self.lines: list[str] = output.split("\n") if isinstance(output, str) else output
        self.output: str = "\n".join(self.lines)
        self.parameters: list[SystemServiceParameterObject] = []

        if not self.is_valid_output(self.output):
            raise KeywordException(f"The output {self.output} was not valid")

        self.table_parser = SystemTableParser(self.lines)
        records = self.table_parser.get_output_values_list()
        for record in records:
            # One param for line
            parameter = SystemServiceParameterObject()
            for key, value in record.items():
                if key == "uuid":
                    parameter.set_uuid(value)
                elif key == "service":
                    parameter.set_service(value)
                elif key == "section":
                    parameter.set_section(value)
                elif key == "name":
                    parameter.set_name(value)
                elif key == "value":
                    parameter.set_value(value)
            self.parameters.append(parameter)

    def get_raw_output(self) -> str:
        """
        Get the raw output from the command.

        Returns:
            str: Raw command output
        """
        return self.output

    def get_parameters(self) -> list[SystemServiceParameterObject]:
        """
        Get the service parameter objects.

        Returns: A list of SystemServiceParameterObject instances
        """
        return self.parameters

    @staticmethod
    def is_valid_output(output: str) -> bool:
        """
        Checks if the output contains valid service parameter data.

        Args:
            output (str): The command output to validate

        Returns:
            bool: True if the output is valid, False otherwise

        """
        if not output.strip():
            # Empty output
            return True

        if not isinstance(output, str):
            get_logger().log_error(f"Output format invalid: {type(output)} should be str")
            return False

        search_set: set[str] = {"uuid", "service", "section", "name", "value"}
        if not all(substring in output for substring in search_set):
            get_logger().log_error(f"Required {search_set} table structure not found in output")
            return False

        return True
