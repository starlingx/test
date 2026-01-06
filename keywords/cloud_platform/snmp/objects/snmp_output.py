from typing import Union

from keywords.cloud_platform.snmp.objects.snmp_object import SNMPObject


class SNMPOutput:
    """Parser for SNMP command output."""

    def __init__(self, command_output: Union[str, list[str]], return_code: int = 0):
        """Constructor.

        Args:
            command_output (Union[str, list[str]]): Raw command output.
            return_code (int): Command return code.
        """
        self._raw_output = command_output
        self._return_code = return_code
        self._snmp_objects = self._parse_output(command_output)

    def _parse_output(self, output: Union[str, list[str]]) -> list[SNMPObject]:
        """Parse command output into SNMP objects.

        Args:
            output (Union[str, list[str]]): Raw command output to parse.

        Returns:
            list[SNMPObject]: List of parsed SNMP objects.
        """
        content = "\n".join(output) if isinstance(output, list) else output
        if not content or not content.strip():
            return []

        # For single SNMP response, create one object
        return [SNMPObject(content.strip())]

    def get_snmp_objects(self) -> list[SNMPObject]:
        """Get SNMP objects.

        Returns:
            list[SNMPObject]: List of parsed SNMP objects.
        """
        return self._snmp_objects

    def get_snmp_object(self) -> SNMPObject:
        """Get first SNMP object for backward compatibility.

        Returns:
            SNMPObject: First SNMP object or empty object if none.
        """
        return self._snmp_objects[0] if self._snmp_objects else SNMPObject("")

    def get_return_code(self) -> int:
        """Get command return code.

        Returns:
            int: Command execution return code.
        """
        return self._return_code

    def is_success(self) -> bool:
        """Check if command was successful.

        Returns:
            bool: True if command succeeded, False otherwise.
        """
        return self._return_code == 0

    def has_valid_data(self) -> bool:
        """Check if output contains valid SNMP data.

        Returns:
            bool: True if valid data present, False otherwise.
        """
        return self.is_success() and any(obj.is_success() for obj in self._snmp_objects)

    def contains_alarm_info(self, alarm_patterns: list[str] = None) -> bool:
        """Check if output contains alarm information.

        Args:
            alarm_patterns (list[str]): Patterns to search for.

        Returns:
            bool: True if alarm info present, False otherwise.
        """
        return any(obj.has_alarm_data(alarm_patterns) for obj in self._snmp_objects)
