"""Object representing a single event from fm event-list output."""


class EventListObject:
    """Holds the parsed fields from a single row of fm event-list."""

    def __init__(self):
        """Initialize EventListObject with explicit fields."""
        self.time_stamp = None
        self.state = None
        self.event_log_id = None
        self.reason_text = None
        self.entity_instance_id = None
        self.severity = None

    def set_time_stamp(self, time_stamp: str) -> None:
        """Set the event timestamp.

        Args:
            time_stamp (str): Timestamp string.
        """
        self.time_stamp = time_stamp

    def get_time_stamp(self) -> str:
        """Get the event timestamp.

        Returns:
            str: Timestamp string.
        """
        return self.time_stamp

    def set_state(self, state: str) -> None:
        """Set the event state.

        Args:
            state (str): Event state (e.g. 'set', 'clear', 'log').
        """
        self.state = state

    def get_state(self) -> str:
        """Get the event state.

        Returns:
            str: Event state (e.g. 'set', 'clear', 'log').
        """
        return self.state

    def set_event_log_id(self, event_log_id: str) -> None:
        """Set the event log ID.

        Args:
            event_log_id (str): Event log ID (e.g. '200.001').
        """
        self.event_log_id = event_log_id

    def get_event_log_id(self) -> str:
        """Get the event log ID.

        Returns:
            str: Event log ID (e.g. '200.001').
        """
        return self.event_log_id

    def set_reason_text(self, reason_text: str) -> None:
        """Set the event reason text.

        Args:
            reason_text (str): Reason text.
        """
        self.reason_text = reason_text

    def get_reason_text(self) -> str:
        """Get the event reason text.

        Returns:
            str: Reason text.
        """
        return self.reason_text

    def set_entity_instance_id(self, entity_instance_id: str) -> None:
        """Set the entity instance ID.

        Args:
            entity_instance_id (str): Entity instance ID (e.g. 'host=compute-0').
        """
        self.entity_instance_id = entity_instance_id

    def get_entity_instance_id(self) -> str:
        """Get the entity instance ID.

        Returns:
            str: Entity instance ID (e.g. 'host=compute-0').
        """
        return self.entity_instance_id

    def set_severity(self, severity: str) -> None:
        """Set the event severity.

        Args:
            severity (str): Severity level.
        """
        self.severity = severity

    def get_severity(self) -> str:
        """Get the event severity.

        Returns:
            str: Severity level.
        """
        return self.severity

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable event summary.
        """
        return (
            f"[ID: {self.get_event_log_id()}, Entity: {self.get_entity_instance_id()}, "
            f"State: {self.get_state()}, Reason: {self.get_reason_text()}]"
        )
