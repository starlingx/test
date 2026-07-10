"""Output parser for Heat stack event SDK responses."""

from typing import List

from keywords.openstack.resources.orchestration.object.heat_stack_event_object import HeatStackEventObject


class HeatStackEventOutput:
    """Parses OpenStack SDK stack event dicts into HeatStackEventObject instances."""

    def __init__(self, raw_events: List[dict]):
        """Initialize and parse event dicts.

        Args:
            raw_events (List[dict]): List of event dicts from SDK to_dict().
        """
        self.events: List[HeatStackEventObject] = []
        for raw in raw_events:
            event = HeatStackEventObject()
            event.set_id(raw.get("id", ""))
            event.set_resource_name(raw.get("resource_name", ""))
            event.set_resource_status(raw.get("resource_status", ""))
            event.set_resource_status_reason(raw.get("resource_status_reason"))
            event.set_event_time(raw.get("event_time"))
            event.set_logical_resource_id(raw.get("logical_resource_id"))
            event.set_physical_resource_id(raw.get("physical_resource_id"))
            event.set_resource_type(raw.get("resource_type"))
            self.events.append(event)

    def get_events(self) -> List[HeatStackEventObject]:
        """Get the list of parsed events.

        Returns:
            List[HeatStackEventObject]: List of event objects.
        """
        return self.events

    def get_events_by_resource_name(self, resource_name: str) -> List[HeatStackEventObject]:
        """Get all events for a specific resource.

        Args:
            resource_name (str): Logical resource name.

        Returns:
            List[HeatStackEventObject]: Events matching the resource name.
        """
        return [e for e in self.events if e.get_resource_name() == resource_name]

    def get_events_by_status(self, status: str) -> List[HeatStackEventObject]:
        """Get all events with a specific status.

        Args:
            status (str): Resource status to filter by.

        Returns:
            List[HeatStackEventObject]: Events matching the status.
        """
        return [e for e in self.events if e.get_resource_status() == status]

    def is_empty(self) -> bool:
        """Check if the output contains no events.

        Returns:
            bool: True if no events in output.
        """
        return len(self.events) == 0
