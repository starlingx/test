"""Cinder backup object representation."""

from typing import Optional


class BackupObject:
    """Represents a single Cinder volume backup."""

    def __init__(self) -> None:
        """Initialize an empty BackupObject."""
        self.id = ""
        self.name = ""
        self.status = ""
        self.volume_id = ""
        self.size = 0
        self.container: Optional[str] = None
        self.description: Optional[str] = None
        self.is_incremental = False
        self.availability_zone: Optional[str] = None
        self.created_at: Optional[str] = None

    def get_id(self) -> str:
        """Get the backup ID.

        Returns:
            str: Backup ID.
        """
        return self.id

    def set_id(self, backup_id: str) -> None:
        """Set the backup ID.

        Args:
            backup_id (str): Backup ID.
        """
        self.id = backup_id

    def get_name(self) -> str:
        """Get the backup name.

        Returns:
            str: Backup name.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set the backup name.

        Args:
            name (str): Backup name.
        """
        self.name = name

    def get_status(self) -> str:
        """Get the backup status.

        Returns:
            str: Backup status (e.g. 'available', 'creating', 'error').
        """
        return self.status

    def set_status(self, status: str) -> None:
        """Set the backup status.

        Args:
            status (str): Backup status.
        """
        self.status = status

    def get_volume_id(self) -> str:
        """Get the source volume ID.

        Returns:
            str: Source volume ID.
        """
        return self.volume_id

    def set_volume_id(self, volume_id: str) -> None:
        """Set the source volume ID.

        Args:
            volume_id (str): Source volume ID.
        """
        self.volume_id = volume_id

    def get_size(self) -> int:
        """Get the backup size in GB.

        Returns:
            int: Backup size in GB.
        """
        return self.size

    def set_size(self, size: int) -> None:
        """Set the backup size in GB.

        Args:
            size (int): Backup size in GB.
        """
        self.size = size

    def get_container(self) -> Optional[str]:
        """Get the backup container name.

        Returns:
            Optional[str]: Container name or None.
        """
        return self.container

    def set_container(self, container: Optional[str]) -> None:
        """Set the backup container name.

        Args:
            container (Optional[str]): Container name.
        """
        self.container = container

    def get_description(self) -> Optional[str]:
        """Get the backup description.

        Returns:
            Optional[str]: Description or None.
        """
        return self.description

    def set_description(self, description: Optional[str]) -> None:
        """Set the backup description.

        Args:
            description (Optional[str]): Description.
        """
        self.description = description

    def get_is_incremental(self) -> bool:
        """Check if the backup is incremental.

        Returns:
            bool: True if incremental backup.
        """
        return self.is_incremental

    def set_incremental(self, incremental: bool) -> None:
        """Set whether backup is incremental.

        Args:
            incremental (bool): True if incremental.
        """
        self.is_incremental = incremental

    def get_availability_zone(self) -> Optional[str]:
        """Get the availability zone.

        Returns:
            Optional[str]: Availability zone or None.
        """
        return self.availability_zone

    def set_availability_zone(self, zone: Optional[str]) -> None:
        """Set the availability zone.

        Args:
            zone (Optional[str]): Availability zone.
        """
        self.availability_zone = zone

    def get_created_at(self) -> Optional[str]:
        """Get the creation timestamp.

        Returns:
            Optional[str]: Creation timestamp string or None.
        """
        return self.created_at

    def set_created_at(self, created_at: Optional[str]) -> None:
        """Set the creation timestamp.

        Args:
            created_at (Optional[str]): Creation timestamp string.
        """
        self.created_at = created_at

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return (
            f"BackupObject(name={self.name}, id={self.id}, "
            f"status={self.status}, volume_id={self.volume_id}, "
            f"size={self.size}GB, incremental={self.is_incremental})"
        )
