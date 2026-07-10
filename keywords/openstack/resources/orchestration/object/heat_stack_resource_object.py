"""Object representing a Heat stack resource."""

from typing import Optional


class HeatStackResourceObject:
    """Holds the parsed fields from a Heat stack resource."""

    def __init__(self):
        """Initialize HeatStackResourceObject with explicit fields."""
        self.resource_name = None
        self.resource_type = None
        self.resource_status = None
        self.resource_status_reason = None
        self.physical_resource_id = None
        self.logical_resource_id = None
        self.updated_time = None

    def set_resource_name(self, resource_name: str) -> None:
        """Set the logical resource name.

        Args:
            resource_name (str): Logical resource name from the template.
        """
        self.resource_name = resource_name

    def get_resource_name(self) -> str:
        """Get the logical resource name.

        Returns:
            str: Logical resource name.
        """
        return self.resource_name

    def set_resource_type(self, resource_type: str) -> None:
        """Set the resource type.

        Args:
            resource_type (str): OpenStack resource type (e.g. 'OS::Cinder::Volume').
        """
        self.resource_type = resource_type

    def get_resource_type(self) -> str:
        """Get the resource type.

        Returns:
            str: OpenStack resource type.
        """
        return self.resource_type

    def set_resource_status(self, resource_status: str) -> None:
        """Set the resource status.

        Args:
            resource_status (str): Resource status (e.g. 'CREATE_COMPLETE').
        """
        self.resource_status = resource_status

    def get_resource_status(self) -> str:
        """Get the resource status.

        Returns:
            str: Resource status.
        """
        return self.resource_status

    def set_resource_status_reason(self, reason: Optional[str]) -> None:
        """Set the resource status reason.

        Args:
            reason (Optional[str]): Reason for current status.
        """
        self.resource_status_reason = reason

    def get_resource_status_reason(self) -> Optional[str]:
        """Get the resource status reason.

        Returns:
            Optional[str]: Reason for current status.
        """
        return self.resource_status_reason

    def set_physical_resource_id(self, physical_resource_id: Optional[str]) -> None:
        """Set the physical resource ID.

        Args:
            physical_resource_id (Optional[str]): Physical ID of the created resource.
        """
        self.physical_resource_id = physical_resource_id

    def get_physical_resource_id(self) -> Optional[str]:
        """Get the physical resource ID.

        Returns:
            Optional[str]: Physical ID of the created resource.
        """
        return self.physical_resource_id

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

    def set_updated_time(self, updated_time: Optional[str]) -> None:
        """Set the update timestamp.

        Args:
            updated_time (Optional[str]): Update timestamp.
        """
        self.updated_time = updated_time

    def get_updated_time(self) -> Optional[str]:
        """Get the update timestamp.

        Returns:
            Optional[str]: Update timestamp.
        """
        return self.updated_time

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable resource summary.
        """
        return f"[Name: {self.get_resource_name()}, Type: {self.get_resource_type()}, Status: {self.get_resource_status()}, PhysicalID: {self.get_physical_resource_id()}]"
