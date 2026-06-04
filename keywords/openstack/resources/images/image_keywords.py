"""Image CRUD keywords via OpenStack SDK."""

import os
import tempfile
import time
import urllib.request
from typing import Optional

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.images.object.image_list_output import ImageListOutput
from keywords.openstack.resources.images.object.image_object import ImageObject


class ImageKeywords(BaseKeyword):
    """CRUD operations for Glance images via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize ImageKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def list_images(self) -> ImageListOutput:
        """List all images.

        Returns:
            ImageListOutput: Parsed image collection.
        """
        raw_images = [i.to_dict() for i in self.openstack_connection.get_image().images()]
        return ImageListOutput(raw_images)

    def show_image(self, image_name_or_id: str) -> ImageObject:
        """Show image details.

        Args:
            image_name_or_id (str): Image name or ID.

        Returns:
            ImageObject: Image details.
        """
        image = self.openstack_connection.get_image().find_image(image_name_or_id, ignore_missing=False)
        return ImageListOutput([image.to_dict()]).get_images()[0]

    def create_image(
        self,
        image_name: str,
        disk_format: str = "qcow2",
        container_format: str = "bare",
        visibility: str = "public",
        source_image: Optional[str] = None,
        hw_firmware_type: Optional[str] = None,
        hw_machine_type: Optional[str] = None,
    ) -> ImageObject:
        """Create an image.

        If source_image is provided, uploads data from that file path.
        Otherwise creates an empty image shell.

        Args:
            image_name (str): Image name.
            disk_format (str): Disk format (e.g. 'qcow2', 'raw').
            container_format (str): Container format (e.g. 'bare').
            visibility (str): Image visibility ('public', 'private', 'shared', 'community').
            source_image (Optional[str]): Path to local image file to upload.
            hw_firmware_type (Optional[str]): Firmware type property (e.g. 'uefi').
            hw_machine_type (Optional[str]): Machine type property (e.g. 'q35').

        Returns:
            ImageObject: Created image details.
        """
        get_logger().log_info(f"Creating image '{image_name}' (disk_format={disk_format})")
        extra = {}
        if hw_firmware_type:
            extra["hw_firmware_type"] = hw_firmware_type
        if hw_machine_type:
            extra["hw_machine_type"] = hw_machine_type

        image_service = self.openstack_connection.get_image()
        if source_image:
            with open(source_image, "rb") as f:
                image = image_service.create_image(
                    name=image_name,
                    disk_format=disk_format,
                    container_format=container_format,
                    visibility=visibility,
                    data=f,
                    **extra,
                )
        else:
            image = image_service.create_image(
                name=image_name,
                disk_format=disk_format,
                container_format=container_format,
                visibility=visibility,
                **extra,
            )
        return ImageListOutput([image.to_dict()]).get_images()[0]

    def _is_web_download_supported(self) -> bool:
        """Check if Glance supports web-download import method.

        Returns:
            bool: True if web-download is available.
        """
        import_info = self.openstack_connection.get_image().get_import_info()
        import_methods = getattr(import_info, "import_methods", None)
        if import_methods is None:
            return False
        available = import_methods.get("value", []) if isinstance(import_methods, dict) else list(import_methods)
        return "web-download" in available

    def create_image_from_url(
        self,
        image_name: str,
        image_url: str,
        disk_format: str = "qcow2",
        container_format: str = "bare",
        visibility: str = "public",
        hw_firmware_type: Optional[str] = None,
        hw_machine_type: Optional[str] = None,
        timeout: int = 30,
    ) -> ImageObject:
        """Create an image by downloading from a URL and uploading to Glance.

        Uses web-download import if supported by Glance, otherwise falls back
        to local download + PUT upload.

        Args:
            image_name (str): Image name.
            image_url (str): URL to download the image from.
            disk_format (str): Disk format (e.g. 'qcow2', 'raw').
            container_format (str): Container format (e.g. 'bare').
            visibility (str): Image visibility ('public', 'private').
            hw_firmware_type (Optional[str]): Firmware type property (e.g. 'uefi').
            hw_machine_type (Optional[str]): Machine type property (e.g. 'q35').
            timeout (int): Seconds to wait for web-download import to start.

        Returns:
            ImageObject: Created image details.
        """
        get_logger().log_info(f"Creating image '{image_name}' from URL: {image_url}")
        if self._is_web_download_supported():
            get_logger().log_info("Glance supports web-download, using import method")
            return self._create_image_via_web_download(
                image_name, image_url, disk_format, container_format,
                visibility, hw_firmware_type, hw_machine_type, timeout,
            )
        get_logger().log_info("web-download not supported, using local download and upload")
        return self._create_image_via_local_download(
            image_name, image_url, disk_format, container_format,
            visibility, hw_firmware_type, hw_machine_type,
        )

    def _create_image_via_web_download(
        self,
        image_name: str,
        image_url: str,
        disk_format: str,
        container_format: str,
        visibility: str,
        hw_firmware_type: Optional[str],
        hw_machine_type: Optional[str],
        timeout: int,
    ) -> ImageObject:
        """Create image using Glance web-download import.

        Creates an image shell, triggers web-download import, and waits
        for the image to leave queued state. Cleans up the shell image
        if import fails.

        Args:
            image_name (str): Image name.
            image_url (str): URL for Glance to download from.
            disk_format (str): Disk format.
            container_format (str): Container format.
            visibility (str): Image visibility.
            hw_firmware_type (Optional[str]): Firmware type property.
            hw_machine_type (Optional[str]): Machine type property.
            timeout (int): Seconds to wait for import to start.

        Returns:
            ImageObject: Created image details.

        Raises:
            RuntimeError: If import fails or image stays queued.
        """
        get_logger().log_info(f"Creating image via web-download import: {image_url}")
        extra = {}
        if hw_firmware_type:
            extra["hw_firmware_type"] = hw_firmware_type
        if hw_machine_type:
            extra["hw_machine_type"] = hw_machine_type

        image_service = self.openstack_connection.get_image()
        image = image_service.create_image(
            name=image_name,
            disk_format=disk_format,
            container_format=container_format,
            visibility=visibility,
            **extra,
        )
        image_service.import_image(image, method="web-download", uri=image_url)
        end_time = time.time() + timeout
        poll_interval = 5
        while time.time() < end_time:
            refreshed = image_service.get_image(image.id)
            if refreshed.status != "queued":
                get_logger().log_info(f"Image import started, status: {refreshed.status}")
                return ImageListOutput([refreshed.to_dict()]).get_images()[0]
            time.sleep(poll_interval)
        image_service.delete_image(image.id)
        raise RuntimeError(f"Image {image.id} stuck in queued after web-download import")

    def _create_image_via_local_download(
        self,
        image_name: str,
        image_url: str,
        disk_format: str,
        container_format: str,
        visibility: str,
        hw_firmware_type: Optional[str],
        hw_machine_type: Optional[str],
    ) -> ImageObject:
        """Download image to a temp file and upload to Glance via PUT.

        Args:
            image_name (str): Image name.
            image_url (str): URL to download the image from.
            disk_format (str): Disk format.
            container_format (str): Container format.
            visibility (str): Image visibility.
            hw_firmware_type (Optional[str]): Firmware type property.
            hw_machine_type (Optional[str]): Machine type property.

        Returns:
            ImageObject: Created image details.
        """
        tmp_path = os.path.join(tempfile.gettempdir(), f"{image_name}.img")
        try:
            get_logger().log_info(f"Downloading image to {tmp_path}")
            urllib.request.urlretrieve(image_url, tmp_path)
            return self.create_image(
                image_name,
                disk_format=disk_format,
                container_format=container_format,
                visibility=visibility,
                source_image=tmp_path,
                hw_firmware_type=hw_firmware_type,
                hw_machine_type=hw_machine_type,
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def set_image_metadata(self, image_name_or_id: str, hw_firmware_type: Optional[str] = None, hw_machine_type: Optional[str] = None) -> ImageObject:
        """Set metadata properties on an image.

        Args:
            image_name_or_id (str): Image name or ID.
            hw_firmware_type (Optional[str]): Firmware type property (e.g. 'uefi').
            hw_machine_type (Optional[str]): Machine type property (e.g. 'q35').

        Returns:
            ImageObject: Updated image details.
        """
        image_service = self.openstack_connection.get_image()
        image = image_service.find_image(image_name_or_id, ignore_missing=False)
        attrs = {}
        if hw_firmware_type:
            attrs["hw_firmware_type"] = hw_firmware_type
        if hw_machine_type:
            attrs["hw_machine_type"] = hw_machine_type
        if attrs:
            get_logger().log_info(f"Setting metadata on image '{image_name_or_id}': {attrs}")
            updated = image_service.update_image(image.id, **attrs)
            return ImageListOutput([updated.to_dict()]).get_images()[0]
        return ImageListOutput([image.to_dict()]).get_images()[0]

    def set_image_visibility(self, image_name_or_id: str, visibility: str) -> ImageObject:
        """Change image visibility.

        Args:
            image_name_or_id (str): Image name or ID.
            visibility (str): Visibility level ('public', 'private', 'shared', 'community').

        Returns:
            ImageObject: Updated image details.
        """
        get_logger().log_info(f"Setting visibility of image '{image_name_or_id}' to '{visibility}'")
        image_service = self.openstack_connection.get_image()
        image = image_service.find_image(image_name_or_id, ignore_missing=False)
        updated = image_service.update_image(image.id, visibility=visibility)
        return ImageListOutput([updated.to_dict()]).get_images()[0]

    def save_image(self, image_name_or_id: str, file_path: str) -> None:
        """Download an image to a local file.

        Args:
            image_name_or_id (str): Image name or ID.
            file_path (str): Local file path to save the image data.
        """
        get_logger().log_info(f"Saving image '{image_name_or_id}' to '{file_path}'")
        image_service = self.openstack_connection.get_image()
        image = image_service.find_image(image_name_or_id, ignore_missing=False)
        data = image_service.download_image(image.id)
        with open(file_path, "wb") as f:
            for chunk in data:
                f.write(chunk)

    def delete_image(self, image_name_or_id: str) -> None:
        """Delete an image.

        Args:
            image_name_or_id (str): Image name or ID.
        """
        get_logger().log_info(f"Deleting image '{image_name_or_id}'")
        image_service = self.openstack_connection.get_image()
        image = image_service.find_image(image_name_or_id, ignore_missing=False)
        image_service.delete_image(image.id)

    def wait_for_image_status(self, image_name_or_id: str, expected_status: str, timeout: int = 120, poll_interval: int = 5) -> ImageObject:
        """Poll until image reaches expected status.

        Args:
            image_name_or_id (str): Image name or ID.
            expected_status (str): Expected status string (e.g. 'active').
            timeout (int): Maximum wait time in seconds.
            poll_interval (int): Seconds between polls.

        Returns:
            ImageObject: Image details once status is reached.

        Raises:
            TimeoutError: If status is not reached within timeout.
            RuntimeError: If image enters killed state.
        """
        image_service = self.openstack_connection.get_image()
        end_time = time.time() + timeout
        while time.time() < end_time:
            image = image_service.find_image(image_name_or_id, ignore_missing=False)
            current_status = image.status.lower()
            if current_status == expected_status.lower():
                get_logger().log_info(f"Image '{image_name_or_id}' reached status '{expected_status}'")
                return ImageListOutput([image.to_dict()]).get_images()[0]
            if current_status == "killed":
                raise RuntimeError(f"Image '{image_name_or_id}' entered killed state")
            get_logger().log_info(f"Image '{image_name_or_id}' status is '{image.status}', waiting for '{expected_status}'...")
            time.sleep(poll_interval)
        raise TimeoutError(f"Image '{image_name_or_id}' did not reach '{expected_status}' within {timeout}s")

    def is_image_gone(self, image_name_or_id: str) -> bool:
        """Check if an image no longer exists.

        Args:
            image_name_or_id (str): Image name or ID.

        Returns:
            bool: True if image is not found.
        """
        return self.openstack_connection.get_image().find_image(image_name_or_id) is None
