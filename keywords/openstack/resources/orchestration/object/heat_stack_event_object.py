"""Object representing a Heat stack event."""

from typing import Optional


class HeatStackEventObject:
    """Holds the parsed fields from a Heat stack event."""

    def __init__(self):
        """Initialize HeatStackEventObject with explicit fields."""
        self.id = None
        self.resource_name = None
        self.resource_status = None
        self.resource_status_reason = None
        self.event_time = None
        self.logical_resource_id = None
        self.physical_resource_id = None
        self.resource_type = None

    def set_id(self, event_id: str) -> None:
        """Set the event ID.

        Args:
            event_id (str): Event ID.
        """
        self.id = event_id

    def get_id(self) -> str:
        """Get the event ID.

        Returns:
            str: Event ID.
        """
        return self.id

    def set_resource_name(self, resource_name: str) -> None:
        """Set the resource name.

        Args:
            resource_name (str): Logical resource name.
        """
        self.resource_name = resource_name

    def get_resource_name(self) -> str:
        """Get the resource name.

        Returns:
            str: Logical resource name.
        """
        return self.resource_name

    def set_resource_status(self, resource_status: str) -> None:
        """Set the resource status at event time.

        Args:
            resource_status (str): Resource status (e.g. 'CREATE_IN_PROGRESS').
        """
        self.resource_status = resource_status

    def get_resource_status(self) -> str:
        """Get the resource status at event time.

        Returns:
            str: Resource status.
        """
        return self.resource_status

    def set_resource_status_reason(self, reason: Optional[str]) -> None:
        """Set the resource status reason.

        Args:
            reason (Optional[str]): Reason for the status transition.
        """
        self.resource_status_reason = reason

    def get_resource_status_reason(self) -> Optional[str]:
        """Get the resource status reason.

        Returns:
            Optional[str]: Reason for the status transition.
        """
        return self.resource_status_reason

    def set_event_time(self, event_time: Optional[str]) -> None:
        """Set the event timestamp.

        Args:
            event_time (Optional[str]): Event timestamp.
        """
        self.event_time = event_time

    def get_event_time(self) -> Optional[str]:
        """Get the event timestamp.

        Returns:
            Optional[str]: Event timestamp.
        """
        return self.event_time

    def set_logical_resource_id(self, logical_resource_id: Optional[str]) -> None:
        """Set the logical resource ID.

        Args:
            logical_resource_id (Optional[str]): Logical resource ID.
        """
        self.logical_resource_id = logical_resource_id

    def get_logical_resource_id(self) -> Optional[str]:
        """Get the logical resource ID.

        Returns:
            Optional[str]: Logical resource ID.
        """
        return self.logical_resource_id

    def set_physical_resource_id(self, physical_resource_id: Optional[str]) -> None:
        """Set the physical resource ID.

        Args:
            physical_resource_id (Optional[str]): Physical resource ID.
        """
        self.physical_resource_id = physical_resource_id

    def get_physical_resource_id(self) -> Optional[str]:
        """Get the physical resource ID.

        Returns:
            Optional[str]: Physical resource ID.
        """
        return self.physical_resource_id

    def set_resource_type(self, resource_type: Optional[str]) -> None:
        """Set the resource type.

        Args:
            resource_type (Optional[str]): OpenStack resource type.
        """
        self.resource_type = resource_type

    def get_resource_type(self) -> Optional[str]:
        """Get the resource type.

        Returns:
            Optional[str]: OpenStack resource type.
        """
        return self.resource_type

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable event summary.
        """
        return f"[ID: {self.get_id()}, Resource: {self.get_resource_name()}, Status: {self.get_resource_status()}, Time: {self.get_event_time()}]"
