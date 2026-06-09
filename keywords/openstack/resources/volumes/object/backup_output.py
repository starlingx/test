"""Backup output parsing and manipulation."""

from typing import Dict

from keywords.openstack.resources.volumes.object.backup_object import BackupObject


class BackupOutput:
    """Wraps a single BackupObject parsed from OpenStack SDK response.

    Provides typed access to backup fields and a place for
    data-manipulation functions related to backup state.
    """

    def __init__(self, raw_backup: Dict) -> None:
        """Initialize BackupOutput from a raw backup dict.

        Args:
            raw_backup (Dict): Backup dictionary from OpenStack SDK (backup.to_dict()).
        """
        self._backup = BackupObject()
        self._backup.set_id(raw_backup.get("id", ""))
        self._backup.set_name(raw_backup.get("name", ""))
        self._backup.set_status(raw_backup.get("status", ""))
        self._backup.set_volume_id(raw_backup.get("volume_id", ""))
        self._backup.set_size(raw_backup.get("size", 0))
        self._backup.set_container(raw_backup.get("container"))
        self._backup.set_description(raw_backup.get("description"))
        self._backup.set_incremental(raw_backup.get("is_incremental", False))
        self._backup.set_availability_zone(raw_backup.get("availability_zone"))
        self._backup.set_created_at(raw_backup.get("created_at"))

    def get_backup_object(self) -> BackupObject:
        """Get the parsed BackupObject.

        Returns:
            BackupObject: Parsed backup.
        """
        return self._backup

    def is_available(self) -> bool:
        """Check if backup is in available state.

        Returns:
            bool: True if status is 'available'.
        """
        return self._backup.get_status().lower() == "available"

    def is_error(self) -> bool:
        """Check if backup is in error state.

        Returns:
            bool: True if status is 'error'.
        """
        return self._backup.get_status().lower() == "error"

    def is_creating(self) -> bool:
        """Check if backup is still being created.

        Returns:
            bool: True if status is 'creating'.
        """
        return self._backup.get_status().lower() == "creating"

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"BackupOutput({self._backup})"
