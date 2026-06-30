"""Output parser for fm event-list command."""

from typing import List

from keywords.cloud_platform.fault_management.events.objects.event_list_object import EventListObject
from keywords.cloud_platform.fault_management.fault_management_table_parser import FaultManagementTableParser


class EventListOutput:
    """Parses fm event-list output and returns a list of EventListObjects."""

    def __init__(self, raw_output: list[str]):
        """Initialize and parse the event-list output.

        Args:
            raw_output (list[str]): Raw CLI output from fm event-list.
        """
        self._events: List[EventListObject] = []
        parser = FaultManagementTableParser(raw_output)
        output_values = parser.get_output_values_list()

        for value in output_values:
            event = EventListObject()
            event.set_time_stamp(value.get("Time Stamp", ""))
            event.set_state(value.get("State", ""))
            event.set_event_log_id(value.get("Event Log ID", ""))
            event.set_reason_text(value.get("Reason Text", ""))
            event.set_entity_instance_id(value.get("Entity Instance ID", ""))
            event.set_severity(value.get("Severity", ""))
            self._events.append(event)

    def get_events(self) -> List[EventListObject]:
        """Get the list of parsed events.

        Returns:
            List[EventListObject]: List of event objects.
        """
        return self._events

    def get_events_by_event_log_id(self, event_log_id: str) -> List[EventListObject]:
        """Get events filtered by event log ID.

        Args:
            event_log_id (str): Event log ID to filter by.

        Returns:
            List[EventListObject]: Matching events.
        """
        return [e for e in self._events if e.get_event_log_id() == event_log_id]

    def get_events_by_entity_instance_id(self, entity_instance_id: str) -> List[EventListObject]:
        """Get events filtered by entity instance ID.

        Args:
            entity_instance_id (str): Entity instance ID to filter by.

        Returns:
            List[EventListObject]: Matching events.
        """
        return [e for e in self._events if e.get_entity_instance_id() == entity_instance_id]
