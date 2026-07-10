"""Object representing a Heat stack."""

from typing import Optional


class HeatStackObject:
    """Holds the parsed fields from a Heat stack."""

    def __init__(self):
        """Initialize HeatStackObject with explicit fields."""
        self.id = None
        self.name = None
        self.status = None
        self.status_reason = None
        self.description = None
        self.creation_time = None
        self.updated_time = None
        self.deletion_time = None

    def set_id(self, stack_id: str) -> None:
        """Set the stack ID.

        Args:
            stack_id (str): Stack ID.
        """
        self.id = stack_id

    def get_id(self) -> str:
        """Get the stack ID.

        Returns:
            str: Stack ID.
        """
        return self.id

    def set_name(self, name: str) -> None:
        """Set the stack name.

        Args:
            name (str): Stack name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the stack name.

        Returns:
            str: Stack name.
        """
        return self.name

    def set_status(self, status: str) -> None:
        """Set the stack status.

        Args:
            status (str): Stack status (e.g. 'CREATE_COMPLETE').
        """
        self.status = status

    def get_status(self) -> str:
        """Get the stack status.

        Returns:
            str: Stack status.
        """
        return self.status

    def set_status_reason(self, status_reason: Optional[str]) -> None:
        """Set the stack status reason.

        Args:
            status_reason (Optional[str]): Reason for current status.
        """
        self.status_reason = status_reason

    def get_status_reason(self) -> Optional[str]:
        """Get the stack status reason.

        Returns:
            Optional[str]: Reason for current status.
        """
        return self.status_reason

    def set_description(self, description: Optional[str]) -> None:
        """Set the stack description.

        Args:
            description (Optional[str]): Stack description.
        """
        self.description = description

    def get_description(self) -> Optional[str]:
        """Get the stack description.

        Returns:
            Optional[str]: Stack description.
        """
        return self.description

    def set_creation_time(self, creation_time: Optional[str]) -> None:
        """Set the creation timestamp.

        Args:
            creation_time (Optional[str]): Creation timestamp.
        """
        self.creation_time = creation_time

    def get_creation_time(self) -> Optional[str]:
        """Get the creation timestamp.

        Returns:
            Optional[str]: Creation timestamp.
        """
        return self.creation_time

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

    def set_deletion_time(self, deletion_time: Optional[str]) -> None:
        """Set the deletion timestamp.

        Args:
            deletion_time (Optional[str]): Deletion timestamp.
        """
        self.deletion_time = deletion_time

    def get_deletion_time(self) -> Optional[str]:
        """Get the deletion timestamp.

        Returns:
            Optional[str]: Deletion timestamp.
        """
        return self.deletion_time

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable stack summary.
        """
        return f"[ID: {self.get_id()}, Name: {self.get_name()}, Status: {self.get_status()}]"
