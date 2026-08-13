"""Object class for FM Event Suppression."""


class FmEventSuppressionObject:
    """Represents an FM event suppression entry."""

    def __init__(self):
        """Initialize FmEventSuppressionObject."""
        self.uuid: str = None
        self.alarm_id: str = None
        self.suppression_status: str = None

    def set_uuid(self, uuid: str):
        """Set the UUID.

        Args:
            uuid (str): The event suppression UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the UUID.

        Returns:
            str: The event suppression UUID.
        """
        return self.uuid

    def set_alarm_id(self, alarm_id: str):
        """Set the alarm ID.

        Args:
            alarm_id (str): The alarm ID.
        """
        self.alarm_id = alarm_id

    def get_alarm_id(self) -> str:
        """Get the alarm ID.

        Returns:
            str: The alarm ID.
        """
        return self.alarm_id

    def set_suppression_status(self, suppression_status: str):
        """Set the suppression status.

        Args:
            suppression_status (str): The suppression status.
        """
        self.suppression_status = suppression_status

    def get_suppression_status(self) -> str:
        """Get the suppression status.

        Returns:
            str: The suppression status.
        """
        return self.suppression_status
