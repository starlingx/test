"""Image object representation."""

from typing import Optional


class ImageObject:
    """Represents a single OpenStack image."""

    def __init__(self) -> None:
        """Initialize an empty ImageObject."""
        self._properties = {}

    def set_property(self, key: str, value: object) -> None:
        """Set a property value.

        Args:
            key (str): Property name.
            value (object): Property value.
        """
        self._properties[key] = value

    def get_property(self, key: str) -> object:
        """Get a property value.

        Args:
            key (str): Property name.

        Returns:
            object: Property value.
        """
        return self._properties.get(key)

    def get_id(self) -> str:
        """Get the image ID.

        Returns:
            str: Image ID.
        """
        return self._properties.get("id", "")

    def set_id(self, image_id: str) -> None:
        """Set the image ID.

        Args:
            image_id (str): Image ID.
        """
        self._properties["id"] = image_id

    def get_name(self) -> str:
        """Get the image name.

        Returns:
            str: Image name.
        """
        return self._properties.get("name", "")

    def set_name(self, name: str) -> None:
        """Set the image name.

        Args:
            name (str): Image name.
        """
        self._properties["name"] = name

    def get_status(self) -> str:
        """Get the image status.

        Returns:
            str: Image status.
        """
        return self._properties.get("status", "")

    def set_status(self, status: str) -> None:
        """Set the image status.

        Args:
            status (str): Image status.
        """
        self._properties["status"] = status

    def get_size(self) -> Optional[int]:
        """Get the image size in bytes.

        Returns:
            Optional[int]: Image size in bytes, or None if unknown.
        """
        return self._properties.get("size")

    def set_size(self, size: Optional[int]) -> None:
        """Set the image size in bytes.

        Args:
            size (Optional[int]): Image size in bytes.
        """
        self._properties["size"] = size

    def get_disk_format(self) -> str:
        """Get the disk format.

        Returns:
            str: Disk format.
        """
        return self._properties.get("disk_format", "")

    def set_disk_format(self, disk_format: str) -> None:
        """Set the disk format.

        Args:
            disk_format (str): Disk format.
        """
        self._properties["disk_format"] = disk_format

    def get_visibility(self) -> str:
        """Get the image visibility.

        Returns:
            str: Image visibility.
        """
        return self._properties.get("visibility", "")

    def set_visibility(self, visibility: str) -> None:
        """Set the image visibility.

        Args:
            visibility (str): Image visibility.
        """
        self._properties["visibility"] = visibility

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"ImageObject(name={self.get_name()}, id={self.get_id()}, status={self.get_status()})"
