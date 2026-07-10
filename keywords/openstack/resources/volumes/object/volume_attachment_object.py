"""Object representing a single Cinder volume attachment."""


class VolumeAttachmentObject:
    """Holds the parsed fields from a volume attachment entry."""

    def __init__(self):
        """Initialize VolumeAttachmentObject."""
        self.server_id = None
        self.attachment_id = None
        self.device = None
        self.volume_id = None

    def set_server_id(self, server_id: str) -> None:
        """Set the attached server ID.

        Args:
            server_id (str): Server ID.
        """
        self.server_id = server_id

    def get_server_id(self) -> str:
        """Get the attached server ID.

        Returns:
            str: Server ID.
        """
        return self.server_id

    def set_attachment_id(self, attachment_id: str) -> None:
        """Set the attachment ID.

        Args:
            attachment_id (str): Attachment ID.
        """
        self.attachment_id = attachment_id

    def get_attachment_id(self) -> str:
        """Get the attachment ID.

        Returns:
            str: Attachment ID.
        """
        return self.attachment_id

    def set_device(self, device: str) -> None:
        """Set the device path on the server.

        Args:
            device (str): Device path (e.g. '/dev/vdb').
        """
        self.device = device

    def get_device(self) -> str:
        """Get the device path on the server.

        Returns:
            str: Device path.
        """
        return self.device

    def set_volume_id(self, volume_id: str) -> None:
        """Set the volume ID.

        Args:
            volume_id (str): Volume ID.
        """
        self.volume_id = volume_id

    def get_volume_id(self) -> str:
        """Get the volume ID.

        Returns:
            str: Volume ID.
        """
        return self.volume_id

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable attachment summary.
        """
        return f"VolumeAttachmentObject(server_id={self.server_id}, device={self.device}, volume_id={self.volume_id})"
