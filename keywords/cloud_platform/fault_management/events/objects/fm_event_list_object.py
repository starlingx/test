class FmEventListObject:
    """Represents a single event from 'fm event-list' output."""

    def __init__(self):
        """Constructor."""
        self.uuid = ""
        self.time_stamp = ""
        self.state = ""
        self.event_log_id = ""
        self.reason_text = ""
        self.entity_instance_id = ""
        self.severity = ""

    def get_uuid(self) -> str:
        """
        Get the event UUID.

        Returns:
            str: The event UUID.
        """
        return self.uuid

    def set_uuid(self, uuid: str) -> None:
        """
        Set the event UUID.

        Args:
            uuid (str): The event UUID.
        """
        self.uuid = uuid

    def get_time_stamp(self) -> str:
        """
        Get the event timestamp.

        Returns:
            str: The event timestamp.
        """
        return self.time_stamp

    def set_time_stamp(self, time_stamp: str) -> None:
        """
        Set the event timestamp.

        Args:
            time_stamp (str): The event timestamp.
        """
        self.time_stamp = time_stamp

    def get_state(self) -> str:
        """
        Get the event state.

        Returns:
            str: The event state.
        """
        return self.state

    def set_state(self, state: str) -> None:
        """
        Set the event state.

        Args:
            state (str): The event state.
        """
        self.state = state

    def get_event_log_id(self) -> str:
        """
        Get the event log ID.

        Returns:
            str: The event log ID.
        """
        return self.event_log_id

    def set_event_log_id(self, event_log_id: str) -> None:
        """
        Set the event log ID.

        Args:
            event_log_id (str): The event log ID.
        """
        self.event_log_id = event_log_id

    def get_reason_text(self) -> str:
        """
        Get the event reason text.

        Returns:
            str: The event reason text.
        """
        return self.reason_text

    def set_reason_text(self, reason_text: str) -> None:
        """
        Set the event reason text.

        Args:
            reason_text (str): The event reason text.
        """
        self.reason_text = reason_text

    def get_entity_instance_id(self) -> str:
        """
        Get the entity instance ID.

        Returns:
            str: The entity instance ID.
        """
        return self.entity_instance_id

    def set_entity_instance_id(self, entity_instance_id: str) -> None:
        """
        Set the entity instance ID.

        Args:
            entity_instance_id (str): The entity instance ID.
        """
        self.entity_instance_id = entity_instance_id

    def get_severity(self) -> str:
        """
        Get the event severity.

        Returns:
            str: The event severity.
        """
        return self.severity

    def set_severity(self, severity: str) -> None:
        """
        Set the event severity.

        Args:
            severity (str): The event severity.
        """
        self.severity = severity
