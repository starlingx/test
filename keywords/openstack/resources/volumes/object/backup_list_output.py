"""Backup list output parsing and manipulation."""

from typing import Dict, List

from keywords.openstack.resources.volumes.object.backup_object import BackupObject


class BackupListOutput:
    """Parses and provides access to a collection of BackupObjects."""

    def __init__(self, raw_backups: List[Dict]) -> None:
        """Initialize BackupListOutput from raw backup dicts.

        Args:
            raw_backups (List[Dict]): List of backup dictionaries from OpenStack SDK.
        """
        self._backups = []
        for raw in raw_backups:
            backup = BackupObject()
            backup.set_id(raw.get("id", ""))
            backup.set_name(raw.get("name", ""))
            backup.set_status(raw.get("status", ""))
            backup.set_volume_id(raw.get("volume_id", ""))
            backup.set_size(raw.get("size", 0))
            backup.set_container(raw.get("container"))
            backup.set_description(raw.get("description"))
            backup.set_incremental(raw.get("is_incremental", False))
            backup.set_availability_zone(raw.get("availability_zone"))
            backup.set_created_at(raw.get("created_at"))
            self._backups.append(backup)

    def get_backups(self) -> List[BackupObject]:
        """Get all backup objects.

        Returns:
            List[BackupObject]: List of backup objects.
        """
        return self._backups

    def get_backup_by_name(self, name: str) -> BackupObject:
        """Get a backup by name.

        Args:
            name (str): Backup name.

        Returns:
            BackupObject: Matching backup.

        Raises:
            ValueError: If no backup with the given name is found.
        """
        for backup in self._backups:
            if backup.get_name() == name:
                return backup
        raise ValueError(f"Backup '{name}' not found")

    def get_backup_by_id(self, backup_id: str) -> BackupObject:
        """Get a backup by ID.

        Args:
            backup_id (str): Backup ID.

        Returns:
            BackupObject: Matching backup.

        Raises:
            ValueError: If no backup with the given ID is found.
        """
        for backup in self._backups:
            if backup.get_id() == backup_id:
                return backup
        raise ValueError(f"Backup with ID '{backup_id}' not found")

    def is_backup_present(self, name: str) -> bool:
        """Check if a backup with the given name exists.

        Args:
            name (str): Backup name.

        Returns:
            bool: True if found.
        """
        for backup in self._backups:
            if backup.get_name() == name:
                return True
        return False

    def get_backups_for_volume(self, volume_id: str) -> List[BackupObject]:
        """Get all backups for a specific volume.

        Args:
            volume_id (str): Volume ID to filter by.

        Returns:
            List[BackupObject]: Backups belonging to the given volume.
        """
        return [b for b in self._backups if b.get_volume_id() == volume_id]

    def get_available_backups(self) -> List[BackupObject]:
        """Get all backups in available state.

        Returns:
            List[BackupObject]: Backups with status 'available'.
        """
        return [b for b in self._backups if b.get_status().lower() == "available"]

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"BackupListOutput(count={len(self._backups)})"
