"""Cinder volume snapshot object representation."""

from typing import Optional


class SnapshotObject:
    """Represents a single Cinder volume snapshot."""

    def __init__(self) -> None:
        """Initialize an empty SnapshotObject."""
        self._id = ""
        self._name = ""
        self._status = ""
        self._volume_id = ""
        self._size = 0
        self._description: Optional[str] = None
        self._created_at: Optional[str] = None

    def get_id(self) -> str:
        """Get the snapshot ID.

        Returns:
            str: Snapshot ID.
        """
        return self._id

    def set_id(self, snapshot_id: str) -> None:
        """Set the snapshot ID.

        Args:
            snapshot_id (str): Snapshot ID.
        """
        self._id = snapshot_id

    def get_name(self) -> str:
        """Get the snapshot name.

        Returns:
            str: Snapshot name.
        """
        return self._name

    def set_name(self, name: str) -> None:
        """Set the snapshot name.

        Args:
            name (str): Snapshot name.
        """
        self._name = name

    def get_status(self) -> str:
        """Get the snapshot status.

        Returns:
            str: Snapshot status (e.g. 'available', 'creating', 'error').
        """
        return self._status

    def set_status(self, status: str) -> None:
        """Set the snapshot status.

        Args:
            status (str): Snapshot status.
        """
        self._status = status

    def get_volume_id(self) -> str:
        """Get the source volume ID.

        Returns:
            str: Source volume ID.
        """
        return self._volume_id

    def set_volume_id(self, volume_id: str) -> None:
        """Set the source volume ID.

        Args:
            volume_id (str): Source volume ID.
        """
        self._volume_id = volume_id

    def get_size(self) -> int:
        """Get the snapshot size in GB.

        Returns:
            int: Snapshot size in GB.
        """
        return self._size

    def set_size(self, size: int) -> None:
        """Set the snapshot size in GB.

        Args:
            size (int): Snapshot size in GB.
        """
        self._size = size

    def get_description(self) -> Optional[str]:
        """Get the snapshot description.

        Returns:
            Optional[str]: Description or None.
        """
        return self._description

    def set_description(self, description: Optional[str]) -> None:
        """Set the snapshot description.

        Args:
            description (Optional[str]): Description.
        """
        self._description = description

    def get_created_at(self) -> Optional[str]:
        """Get the creation timestamp.

        Returns:
            Optional[str]: Creation timestamp string or None.
        """
        return self._created_at

    def set_created_at(self, created_at: Optional[str]) -> None:
        """Set the creation timestamp.

        Args:
            created_at (Optional[str]): Creation timestamp string.
        """
        self._created_at = created_at
