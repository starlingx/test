"""Image list output parsing and manipulation."""

from typing import Dict, List, Optional

from framework.logging.automation_logger import get_logger

from keywords.openstack.resources.images.object.image_object import ImageObject


class ImageListOutput:
    """Parses and provides access to a collection of ImageObjects."""

    def __init__(self, raw_images: List[Dict]) -> None:
        """Initialize ImageListOutput from raw image dicts.

        Args:
            raw_images (List[Dict]): List of image dictionaries from OpenStack SDK.
        """
        self._images = []
        for raw in raw_images:
            image = ImageObject()
            image.set_id(raw.get("id", ""))
            image.set_name(raw.get("name", ""))
            image.set_status(raw.get("status", ""))
            image.set_size(raw.get("size"))
            image.set_disk_format(raw.get("disk_format", ""))
            image.set_visibility(raw.get("visibility", ""))
            self._images.append(image)

    def get_images(self) -> List[ImageObject]:
        """Get all image objects.

        Returns:
            List[ImageObject]: List of image objects.
        """
        return self._images

    def get_image_by_name(self, name: str) -> ImageObject:
        """Get an image by name.

        Args:
            name (str): Image name.

        Returns:
            ImageObject: Matching image.

        Raises:
            ValueError: If no image with the given name is found.
        """
        for image in self._images:
            if image.get_name() == name:
                return image
        raise ValueError(f"Image '{name}' not found")

    def is_image_present(self, name: str) -> bool:
        """Check if an image with the given name exists.

        Args:
            name (str): Image name.

        Returns:
            bool: True if found.
        """
        for image in self._images:
            if image.get_name() == name:
                return True
        return False

    def find_by_name_contains(self, substring: str, status: str = "active") -> Optional[ImageObject]:
        """Find the first image whose name contains the given substring.

        Args:
            substring (str): Substring to search for (case-insensitive).
            status (str): Required image status.

        Returns:
            Optional[ImageObject]: Matching image, or None if not found.
        """
        for image in self._images:
            if image.get_status() == status and substring.lower() in image.get_name().lower():
                return image
        return None

    def discover_image(self) -> ImageObject:
        """Discover a suitable active image for tests.

        Prefers active cirros images (small, fast). Falls back to the
        smallest active image by size. Images with unknown size are
        considered last.

        Returns:
            ImageObject: Discovered image.

        Raises:
            RuntimeError: If no active images are available.
        """
        active_images = [img for img in self._images if img.get_status() == "active"]
        if not active_images:
            raise RuntimeError("No active images found in Glance")

        for img in active_images:
            if "cirros" in img.get_name().lower():
                get_logger().log_info(f"Discovered image: {img.get_name()} ({img.get_id()})")
                return img

        images_with_size = [img for img in active_images if img.get_size() is not None]
        if images_with_size:
            smallest = min(images_with_size, key=lambda i: i.get_size())
        else:
            smallest = active_images[0]
        get_logger().log_info(f"No cirros image found, using smallest: {smallest.get_name()} ({smallest.get_id()})")
        return smallest

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return f"ImageListOutput(count={len(self._images)})"
