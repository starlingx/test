"""Object representing a single alarm from fm alarm-show output."""


class AlarmShowObject:
    """Holds the parsed fields from fm alarm-show <uuid>."""

    def __init__(self):
        """Initialize AlarmShowObject with explicit fields."""
        self.uuid = None
        self.alarm_id = None
        self.alarm_state = None
        self.entity_instance_id = None
        self.severity = None
        self.reason_text = None
        self.alarm_type = None
        self.probable_cause = None
        self.proposed_repair_action = None
        self.service_affecting = None
        self.suppression = None
        self.timestamp = None

    def set_uuid(self, uuid: str) -> None:
        """Set the alarm UUID.

        Args:
            uuid (str): Alarm UUID.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Get the alarm UUID.

        Returns:
            str: Alarm UUID.
        """
        return self.uuid

    def set_alarm_id(self, alarm_id: str) -> None:
        """Set the alarm ID.

        Args:
            alarm_id (str): Alarm ID (e.g. '200.001').
        """
        self.alarm_id = alarm_id

    def get_alarm_id(self) -> str:
        """Get the alarm ID.

        Returns:
            str: Alarm ID (e.g. '200.001').
        """
        return self.alarm_id

    def set_alarm_state(self, alarm_state: str) -> None:
        """Set the alarm state.

        Args:
            alarm_state (str): Alarm state (e.g. 'set', 'clear').
        """
        self.alarm_state = alarm_state

    def get_alarm_state(self) -> str:
        """Get the alarm state.

        Returns:
            str: Alarm state (e.g. 'set', 'clear').
        """
        return self.alarm_state

    def set_entity_instance_id(self, entity_instance_id: str) -> None:
        """Set the entity instance ID.

        Args:
            entity_instance_id (str): Entity instance ID (e.g. 'host=controller-1').
        """
        self.entity_instance_id = entity_instance_id

    def get_entity_instance_id(self) -> str:
        """Get the entity instance ID.

        Returns:
            str: Entity instance ID (e.g. 'host=controller-1').
        """
        return self.entity_instance_id

    def set_severity(self, severity: str) -> None:
        """Set the alarm severity.

        Args:
            severity (str): Severity (e.g. 'warning', 'major', 'critical').
        """
        self.severity = severity

    def get_severity(self) -> str:
        """Get the alarm severity.

        Returns:
            str: Severity (e.g. 'warning', 'major', 'critical').
        """
        return self.severity

    def set_reason_text(self, reason_text: str) -> None:
        """Set the alarm reason text.

        Args:
            reason_text (str): Reason text describing the alarm.
        """
        self.reason_text = reason_text

    def get_reason_text(self) -> str:
        """Get the alarm reason text.

        Returns:
            str: Reason text describing the alarm.
        """
        return self.reason_text

    def set_alarm_type(self, alarm_type: str) -> None:
        """Set the alarm type.

        Args:
            alarm_type (str): Alarm type.
        """
        self.alarm_type = alarm_type

    def get_alarm_type(self) -> str:
        """Get the alarm type.

        Returns:
            str: Alarm type.
        """
        return self.alarm_type

    def set_probable_cause(self, probable_cause: str) -> None:
        """Set the probable cause.

        Args:
            probable_cause (str): Probable cause description.
        """
        self.probable_cause = probable_cause

    def get_probable_cause(self) -> str:
        """Get the probable cause.

        Returns:
            str: Probable cause description.
        """
        return self.probable_cause

    def set_proposed_repair_action(self, proposed_repair_action: str) -> None:
        """Set the proposed repair action.

        Args:
            proposed_repair_action (str): Proposed repair action.
        """
        self.proposed_repair_action = proposed_repair_action

    def get_proposed_repair_action(self) -> str:
        """Get the proposed repair action.

        Returns:
            str: Proposed repair action.
        """
        return self.proposed_repair_action

    def set_service_affecting(self, service_affecting: str) -> None:
        """Set whether the alarm is service affecting.

        Args:
            service_affecting (str): Service affecting value (e.g. 'True', 'False').
        """
        self.service_affecting = service_affecting

    def get_service_affecting(self) -> str:
        """Get whether the alarm is service affecting.

        Returns:
            str: Service affecting value.
        """
        return self.service_affecting

    def set_suppression(self, suppression: str) -> None:
        """Set the alarm suppression status.

        Args:
            suppression (str): Suppression value (e.g. 'True', 'False').
        """
        self.suppression = suppression

    def get_suppression(self) -> str:
        """Get the alarm suppression status.

        Returns:
            str: Suppression value.
        """
        return self.suppression

    def set_timestamp(self, timestamp: str) -> None:
        """Set the alarm timestamp.

        Args:
            timestamp (str): Timestamp string.
        """
        self.timestamp = timestamp

    def get_timestamp(self) -> str:
        """Get the alarm timestamp.

        Returns:
            str: Timestamp string.
        """
        return self.timestamp

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable alarm summary.
        """
        return (
            f"[UUID: {self.get_uuid()}, ID: {self.get_alarm_id()}, "
            f"Entity: {self.get_entity_instance_id()}, Severity: {self.get_severity()}]"
        )
