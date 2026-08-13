"""Object class for FM Event Log."""


class FmEventLogObject:
    """Represents an FM event log entry."""

    def __init__(self):
        """Initialize FmEventLogObject."""
        self.event_log_id: str = None
        self.reason_text: str = None
        self.entity_instance_id: str = None
        self.severity: str = None
        self.timestamp: str = None
        self.state: str = None

    def set_event_log_id(self, event_log_id: str):
        """Set the event log ID.

        Args:
            event_log_id (str): The event log ID.
        """
        self.event_log_id = event_log_id

    def get_event_log_id(self) -> str:
        """Get the event log ID.

        Returns:
            str: The event log ID.
        """
        return self.event_log_id

    def set_reason_text(self, reason_text: str):
        """Set the reason text.

        Args:
            reason_text (str): The reason text.
        """
        self.reason_text = reason_text

    def get_reason_text(self) -> str:
        """Get the reason text.

        Returns:
            str: The reason text.
        """
        return self.reason_text

    def set_entity_instance_id(self, entity_instance_id: str):
        """Set the entity instance ID.

        Args:
            entity_instance_id (str): The entity instance ID.
        """
        self.entity_instance_id = entity_instance_id

    def get_entity_instance_id(self) -> str:
        """Get the entity instance ID.

        Returns:
            str: The entity instance ID.
        """
        return self.entity_instance_id

    def set_severity(self, severity: str):
        """Set the severity.

        Args:
            severity (str): The severity.
        """
        self.severity = severity

    def get_severity(self) -> str:
        """Get the severity.

        Returns:
            str: The severity.
        """
        return self.severity

    def set_timestamp(self, timestamp: str):
        """Set the timestamp.

        Args:
            timestamp (str): The timestamp.
        """
        self.timestamp = timestamp

    def get_timestamp(self) -> str:
        """Get the timestamp.

        Returns:
            str: The timestamp.
        """
        return self.timestamp

    def set_state(self, state: str):
        """Set the state.

        Args:
            state (str): The state.
        """
        self.state = state

    def get_state(self) -> str:
        """Get the state.

        Returns:
            str: The state.
        """
        return self.state
