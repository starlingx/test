import re
from typing import Union

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemServiceParameterOutput:
    """Parses output of 'system service-parameter-add/modify' commands.

    Handles multiple parameter tables in a single output.

    Args:
        output (Union[str, list]): Raw output from 'system service-parameter-...' command

    Sample Output:
    There are multiple tables

    +-------------+--------------------------------------+
    | Property    | Value                                |
    +-------------+--------------------------------------+
    | name        | vm.swappiness                        |
    | personality | None                                 |
    | resource    | None                                 |
    | section     | sysctl                               |
    | service     | platform                             |
    | uuid        | cb5733ce-4bac-4caa-a85d-918ecb78aa75 |
    | value       | 10                                   |
    +-------------+--------------------------------------+
    +-------------+--------------------------------------+
    | Property    | Value                                |
    +-------------+--------------------------------------+
    | name        | kernel.panic_print                   |
    | personality | None                                 |
    | resource    | None                                 |
    | section     | sysctl                               |
    | service     | platform                             |
    | uuid        | c3e8706f-ab09-4327-ad61-4d0c6e602ed3 |
    | value       | 0                                    |
    +-------------+--------------------------------------+
    +-------------+--------------------------------------+
    | Property    | Value                                |
    +-------------+--------------------------------------+
    | name        | kernel.pid_max                       |
    | personality | None                                 |
    | resource    | None                                 |
    | section     | sysctl                               |
    | service     | platform                             |
    | uuid        | f789e402-23b1-4d9a-8c5e-9f3a2d1b0c4e |
    | value       | 4194304                              |
    +-------------+--------------------------------------+
    """

    def __init__(self, output: Union[str, list]):

        self.lines: list[str] = output.split("\n") if isinstance(output, str) else output
        self.output: str = "\n".join(self.lines)
        self.parameters: list[SystemServiceParameterObject] = []

        if not self.is_valid_output(self.output):
            raise KeywordException(f"The output {output} was not valid")

        clean_lines: list[str] = [line for line in self.lines if line.strip()]
        clean_output: str = "".join(clean_lines)
        tbl_pattern = r"\+[-+]+\+"  # Pattern of table string
        marked_output = re.sub(f"({tbl_pattern})\n(?={tbl_pattern})", r"\1\n\n", clean_output)  # Add '\n\n' between tables
        tables: list[str] = [table.strip() for table in marked_output.split("\n\n") if table.strip()]
        for table_str in tables:
            parameter = self._parse_table(table_str)
            if parameter:
                self.parameters.append(parameter)

    def _parse_table(self, table_str: str) -> SystemServiceParameterObject | None:
        """
        Parse table string and return a parameter object

        Sample Output :

        +-------------+--------------------------------------+
        | Property    | Value                                |
        +-------------+--------------------------------------+
        | name        | kernel.panic_print                   |
        | personality | None                                 |
        | resource    | None                                 |
        | section     | sysctl                               |
        | service     | platform                             |
        | uuid        | c3e8706f-ab09-4327-ad61-4d0c6e602ed3 |
        | value       | 0                                    |
        +-------------+--------------------------------------+

        """
        if not self.is_valid_output(table_str):
            raise KeywordException(f"The output {table_str} was not valid")

        table_lines: list[str] = table_str.split("\n")
        records = SystemTableParser(table_lines).get_output_values_list()

        # Convert Property/Value pairs to a single parameter object
        # object_attributes = {"service", "section", "name", "value", "uuid"}
        parameter = SystemServiceParameterObject()
        object_attributes = {name[4:] for name in dir(parameter) if name.startswith("get_") and callable(getattr(parameter, name))}

        updated = False
        for record in records:
            attribute = record.get("Property", "")
            value = record.get("Value", "")
            if attribute in object_attributes:
                setter = getattr(parameter, f"set_{attribute}", None)
                if setter:
                    setter(value)
                    updated = True

        return parameter if updated else None

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

        search_set: set[str] = {"Property", "Value"}
        if not all(substring in output for substring in search_set):
            get_logger().log_error(f"Required {search_set} table structure not found in output")
            return False

        return True
