"""Object representing a Cinder volume."""

from typing import List

from keywords.openstack.resources.volumes.object.volume_attachment_object import VolumeAttachmentObject


class VolumeObject:
    """Holds the parsed fields from a Cinder volume."""

    def __init__(self):
        """Initialize VolumeObject with explicit fields."""
        self.id = None
        self.name = None
        self.status = None
        self.size = None
        self.volume_type = None
        self.availability_zone = None
        self.bootable = None
        self.created_at = None
        self.updated_at = None
        self.attachments = None
        self.host = None

    def set_id(self, volume_id: str) -> None:
        """Set the volume ID.

        Args:
            volume_id (str): Volume ID.
        """
        self.id = volume_id

    def get_id(self) -> str:
        """Get the volume ID.

        Returns:
            str: Volume ID.
        """
        return self.id

    def set_name(self, name: str) -> None:
        """Set the volume name.

        Args:
            name (str): Volume name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the volume name.

        Returns:
            str: Volume name.
        """
        return self.name

    def set_status(self, status: str) -> None:
        """Set the volume status.

        Args:
            status (str): Volume status (e.g. 'available', 'in-use', 'error').
        """
        self.status = status

    def get_status(self) -> str:
        """Get the volume status.

        Returns:
            str: Volume status.
        """
        return self.status

    def set_size(self, size: int) -> None:
        """Set the volume size in GB.

        Args:
            size (int): Volume size in GB.
        """
        self.size = size

    def get_size(self) -> int:
        """Get the volume size in GB.

        Returns:
            int: Volume size in GB.
        """
        return self.size

    def set_volume_type(self, volume_type: str) -> None:
        """Set the volume type.

        Args:
            volume_type (str): Volume type name.
        """
        self.volume_type = volume_type

    def get_volume_type(self) -> str:
        """Get the volume type.

        Returns:
            str: Volume type name.
        """
        return self.volume_type

    def set_availability_zone(self, availability_zone: str) -> None:
        """Set the availability zone.

        Args:
            availability_zone (str): Availability zone.
        """
        self.availability_zone = availability_zone

    def get_availability_zone(self) -> str:
        """Get the availability zone.

        Returns:
            str: Availability zone.
        """
        return self.availability_zone

    def set_bootable(self, bootable: str) -> None:
        """Set whether the volume is bootable.

        Args:
            bootable (str): 'true' or 'false'.
        """
        self.bootable = bootable

    def get_bootable(self) -> str:
        """Get whether the volume is bootable.

        Returns:
            str: 'true' or 'false'.
        """
        return self.bootable

    def set_created_at(self, created_at: str) -> None:
        """Set the creation timestamp.

        Args:
            created_at (str): Creation timestamp.
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """Get the creation timestamp.

        Returns:
            str: Creation timestamp.
        """
        return self.created_at

    def set_updated_at(self, updated_at: str) -> None:
        """Set the update timestamp.

        Args:
            updated_at (str): Update timestamp.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """Get the update timestamp.

        Returns:
            str: Update timestamp.
        """
        return self.updated_at

    def set_attachments(self, attachments: list) -> None:
        """Set the volume attachments.

        Args:
            attachments (list): List of attachment dicts.
        """
        self.attachments = attachments

    def get_attachments(self) -> list:
        """Get the volume attachments as raw dicts.

        Returns:
            list: List of attachment dicts.
        """
        return self.attachments or []

    def get_attachment_objects(self) -> List[VolumeAttachmentObject]:
        """Get the volume attachments as typed objects.

        Returns:
            List[VolumeAttachmentObject]: List of attachment objects.
        """
        result = []
        for raw in self.get_attachments():
            obj = VolumeAttachmentObject()
            obj.set_server_id(raw.get("server_id"))
            obj.set_attachment_id(raw.get("attachment_id") or raw.get("id"))
            obj.set_device(raw.get("device"))
            obj.set_volume_id(raw.get("volume_id"))
            result.append(obj)
        return result

    def is_attached(self) -> bool:
        """Check if the volume is attached to any server.

        Returns:
            bool: True if volume has attachments.
        """
        return len(self.get_attachments()) > 0

    def is_attached_to_server(self, server_id: str) -> bool:
        """Check if the volume is attached to a specific server.

        Args:
            server_id (str): Server ID to check.

        Returns:
            bool: True if volume is attached to the given server.
        """
        for attachment in self.get_attachment_objects():
            if attachment.get_server_id() == server_id:
                return True
        return False

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable volume summary.
        """
        return f"[ID: {self.get_id()}, Name: {self.get_name()}, Status: {self.get_status()}, Size: {self.get_size()}GB]"
    
    def set_host(self, host: str) -> None:
        """Set the volume host (backend).

        Args:
            host (str): Volume host string (e.g. 'cinder@ceph-rook-store#ceph-rook-store').
        """
        self.host = host

    def get_host(self) -> str:
        """Get the volume host (backend).

        Returns:
            str: Volume host string.
        """
        return self.host