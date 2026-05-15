class AlarmListObject:
    """Class to hold attributes of an alarm as returned by alarm list command."""

    def __init__(
        self,
    ):
        self.uuid = None
        self.alarm_id = None
        self.reason_text = None
        self.entity_id = None
        self.severity = None
        self.time_stamp = None

    def __str__(self) -> str:
        """String representation of this object."""
        alarm_id = self.get_alarm_id() or ""
        reason_text = self.get_reason_text() or ""
        entity_id = self.get_entity_id() or ""
        return f"[ID: {alarm_id}, Reason: {reason_text}, Entity: {entity_id}]"

    def set_uuid(self, uuid: str):
        """Setter for UUID.

        Args:
            uuid (str): The alarm UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Getter for UUID.

        Returns:
            str: The alarm UUID, or None if not available.
        """
        return self.uuid

    def set_alarm_id(self, alarm_id: str):
        """Setter for alarm id.

        Args:
            alarm_id (str): The id of the alarm.
        """
        self.alarm_id = alarm_id

    def get_alarm_id(self) -> str:
        """Getter for alarm id.

        Returns:
            str: The alarm id.
        """
        return self.alarm_id

    def set_reason_text(self, reason_text: str):
        """Setter for reason text.

        Args:
            reason_text (str): The reason text.
        """
        self.reason_text = reason_text

    def get_reason_text(self) -> str:
        """Getter for reason text.

        Returns:
            str: The reason text.
        """
        return self.reason_text

    def set_entity_id(self, entity_id: str):
        """Setter for entity id.

        Args:
            entity_id (str): The entity id.
        """
        self.entity_id = entity_id

    def get_entity_id(self) -> str:
        """Getter for entity id.

        Returns:
            str: The entity id.
        """
        return self.entity_id

    def set_severity(self, severity: str):
        """Setter for severity.

        Args:
            severity (str): The severity.
        """
        self.severity = severity

    def get_severity(self) -> str:
        """Getter for severity.

        Returns:
            str: The severity.
        """
        return self.severity

    def set_time_stamp(self, time_stamp: str):
        """Setter for time stamp.

        Args:
            time_stamp (str): The time stamp.
        """
        self.time_stamp = time_stamp

    def get_time_stamp(self) -> str:
        """Getter for time stamp.

        Returns:
            str: The time stamp.
        """
        return self.time_stamp

    def __eq__(self, alarm_list_object):
        """Check equality based on alarm_id, severity, and entity_id."""
        if not isinstance(alarm_list_object, AlarmListObject):
            return False
        return self.get_alarm_id() == alarm_list_object.get_alarm_id() and self.get_severity() == alarm_list_object.get_severity() and self.get_entity_id() == alarm_list_object.get_entity_id()
