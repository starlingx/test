class SNMPObject:
    """Object representing SNMP command result."""

    def __init__(self, content: str):
        """Constructor.

        Args:
            content (str): SNMP command output content.
        """
        self._content = content

    def get_content(self) -> str:
        """Get SNMP content.

        Returns:
            str: SNMP output content.
        """
        return self._content

    def contains_alarm_id(self, alarm_id: str) -> bool:
        """Check if output contains specific alarm ID.

        Args:
            alarm_id (str): Alarm ID to search for.

        Returns:
            bool: True if alarm ID found, False otherwise.
        """
        return alarm_id in self._content

    def contains_oid(self, oid: str) -> bool:
        """Check if output contains specific OID.

        Args:
            oid (str): OID to search for.

        Returns:
            bool: True if OID found, False otherwise.
        """
        return oid in self._content

    def is_empty(self) -> bool:
        """Check if content is empty.

        Returns:
            bool: True if empty, False otherwise.
        """
        return not self._content.strip()

    def is_success(self) -> bool:
        """Check if SNMP operation was successful.

        Returns:
            bool: True if successful, False otherwise.
        """
        error_patterns = ["Invalid OID", "No Such Object", "No more variables"]
        return not any(pattern in self._content for pattern in error_patterns)

    def has_alarm_data(self, alarm_patterns: list[str] = None) -> bool:
        """Check if content contains alarm data.

        Args:
            alarm_patterns (list[str]): Patterns to search for. If None, uses default patterns.

        Returns:
            bool: True if alarm data present, False otherwise.
        """
        if alarm_patterns is None:
            alarm_patterns = ["300.005", "CGCSAuto"]
        return any(pattern in self._content for pattern in alarm_patterns)
