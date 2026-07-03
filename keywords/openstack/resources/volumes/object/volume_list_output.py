"""Output parser for Cinder volume SDK responses."""

from typing import List

from keywords.openstack.resources.volumes.object.volume_object import VolumeObject


class VolumeListOutput:
    """Parses OpenStack SDK volume dicts into VolumeObject instances."""

    def __init__(self, raw_volumes: List[dict]):
        """Initialize and parse volume dicts.

        Args:
            raw_volumes (List[dict]): List of volume dicts from SDK to_dict().
        """
        self._volumes: List[VolumeObject] = []
        for raw in raw_volumes:
            volume = VolumeObject()
            volume.set_id(raw.get("id", ""))
            volume.set_name(raw.get("name", ""))
            volume.set_status(raw.get("status", ""))
            volume.set_size(raw.get("size", 0))
            volume.set_volume_type(raw.get("volume_type", ""))
            volume.set_availability_zone(raw.get("availability_zone", ""))
            volume.set_bootable(raw.get("bootable", "false"))
            volume.set_created_at(raw.get("created_at", ""))
            volume.set_updated_at(raw.get("updated_at", ""))
            volume.set_attachments(raw.get("attachments", []))
            volume.set_host(raw.get("host"))
            self._volumes.append(volume)

    def get_volumes(self) -> List[VolumeObject]:
        """Get the list of parsed volumes.

        Returns:
            List[VolumeObject]: List of volume objects.
        """
        return self._volumes

    def get_volume_by_name(self, name: str) -> VolumeObject:
        """Get a volume by name.

        Args:
            name (str): Volume name.

        Returns:
            VolumeObject: Matching volume.

        Raises:
            KeyError: If no volume with that name is found.
        """
        for volume in self._volumes:
            if volume.get_name() == name:
                return volume
        raise KeyError(f"Volume '{name}' not found")

    def get_volume_by_id(self, volume_id: str) -> VolumeObject:
        """Get a volume by ID.

        Args:
            volume_id (str): Volume ID.

        Returns:
            VolumeObject: Matching volume.

        Raises:
            KeyError: If no volume with that ID is found.
        """
        for volume in self._volumes:
            if volume.get_id() == volume_id:
                return volume
        raise KeyError(f"Volume with ID '{volume_id}' not found")
