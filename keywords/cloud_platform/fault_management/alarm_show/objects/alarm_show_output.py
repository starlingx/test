"""Output parser for fm alarm-show command."""

from keywords.cloud_platform.fault_management.alarm_show.objects.alarm_show_object import AlarmShowObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class AlarmShowOutput:
    """Parses fm alarm-show output and returns an AlarmShowObject."""

    def __init__(self, raw_output: list[str]):
        """Initialize and parse the alarm-show output.

        Args:
            raw_output (list[str]): Raw CLI output from fm alarm-show.
        """
        self._alarm = AlarmShowObject()
        parser = SystemVerticalTableParser(raw_output)
        values = parser.get_output_values_dict()

        self._alarm.set_uuid(values.get("uuid", ""))
        self._alarm.set_alarm_id(values.get("alarm_id", ""))
        self._alarm.set_alarm_state(values.get("alarm_state", ""))
        self._alarm.set_entity_instance_id(values.get("entity_instance_id", ""))
        self._alarm.set_severity(values.get("severity", ""))
        self._alarm.set_reason_text(values.get("reason_text", ""))
        self._alarm.set_alarm_type(values.get("alarm_type", ""))
        self._alarm.set_probable_cause(values.get("probable_cause", ""))
        self._alarm.set_proposed_repair_action(values.get("proposed_repair_action", ""))
        self._alarm.set_service_affecting(values.get("service_affecting", ""))
        self._alarm.set_suppression(values.get("suppression", ""))
        self._alarm.set_timestamp(values.get("timestamp", ""))

    def get_alarm_show_object(self) -> AlarmShowObject:
        """Get the parsed alarm object.

        Returns:
            AlarmShowObject: Parsed alarm data.
        """
        return self._alarm
