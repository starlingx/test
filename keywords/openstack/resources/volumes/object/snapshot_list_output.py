"""Snapshot list output parsing and manipulation."""

from typing import Dict, List

from keywords.openstack.resources.volumes.object.snapshot_object import SnapshotObject


class SnapshotListOutput:
    """Parses and provides access to a collection of SnapshotObjects."""

    def __init__(self, raw_snapshots: List[Dict]) -> None:
        """Initialize SnapshotListOutput from raw snapshot dicts.

        Args:
            raw_snapshots (List[Dict]): List of snapshot dictionaries from OpenStack SDK.
        """
        self._snapshots: List[SnapshotObject] = []
        for raw in raw_snapshots:
            snapshot = SnapshotObject()
            snapshot.set_id(raw.get("id", ""))
            snapshot.set_name(raw.get("name", ""))
            snapshot.set_status(raw.get("status", ""))
            snapshot.set_volume_id(raw.get("volume_id", ""))
            snapshot.set_size(raw.get("size", 0))
            snapshot.set_description(raw.get("description"))
            snapshot.set_created_at(raw.get("created_at"))
            self._snapshots.append(snapshot)

    def get_snapshots(self) -> List[SnapshotObject]:
        """Get all snapshot objects.

        Returns:
            List[SnapshotObject]: List of snapshot objects.
        """
        return self._snapshots

    def get_snapshot_by_name(self, name: str) -> SnapshotObject:
        """Get a snapshot by name.

        Args:
            name (str): Snapshot name.

        Returns:
            SnapshotObject: Matching snapshot.

        Raises:
            ValueError: If no snapshot with the given name is found.
        """
        for snapshot in self._snapshots:
            if snapshot.get_name() == name:
                return snapshot
        raise ValueError(f"Snapshot '{name}' not found")

    def get_snapshot_by_id(self, snapshot_id: str) -> SnapshotObject:
        """Get a snapshot by ID.

        Args:
            snapshot_id (str): Snapshot ID.

        Returns:
            SnapshotObject: Matching snapshot.

        Raises:
            ValueError: If no snapshot with the given ID is found.
        """
        for snapshot in self._snapshots:
            if snapshot.get_id() == snapshot_id:
                return snapshot
        raise ValueError(f"Snapshot with ID '{snapshot_id}' not found")
