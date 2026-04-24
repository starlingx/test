"""Keywords for downloading files from a JSON5 image manifest."""

from typing import Optional

import json5

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.wget.wget_keywords import WgetKeywords


class ImageManifestKeywords(BaseKeyword):
    """Keywords for downloading files defined in a JSON5 manifest.

    Loads image/file definitions from a JSON5 manifest and provides methods
    to look up entries and download files by logical name. The manifest is
    a simple JSON5 file with an ``images`` map keyed by logical name.

    Manifest format::

        {
          "images": {
            "my-image": {
              "url": "https://example.com/my-image.qcow2",
              "filename": "my-image.qcow2"
            }
          }
        }

    Example::

        manifest = ImageManifestKeywords(ssh_connection, "/path/to/manifest.json5")
        local_path = manifest.download_image("my-image", "/home/sysadmin/images")
        # -> /home/sysadmin/images/my-image.qcow2
    """

    def __init__(self, ssh_connection: SSHConnection, manifest_path: str):
        """Initialize ImageManifestKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            manifest_path (str): Absolute path to the JSON5 manifest file.
        """
        self._ssh_connection: SSHConnection = ssh_connection
        self._manifest_path: str = manifest_path
        self._manifest_data: Optional[dict] = None

    def _load_manifest(self) -> dict:
        """Load and cache the manifest.

        Returns:
            dict: Parsed manifest data.

        Raises:
            KeywordException: If the manifest file cannot be loaded.
        """
        if self._manifest_data is not None:
            return self._manifest_data

        get_logger().log_info(f"Loading image manifest: {self._manifest_path}")
        try:
            with open(self._manifest_path, "r") as f:
                self._manifest_data = json5.load(f)
        except Exception as e:
            raise KeywordException(f"Failed to load image manifest '{self._manifest_path}': {e}") from e

        return self._manifest_data

    def get_image_entry(self, image_name: str) -> dict:
        """Look up an image entry by logical name.

        Args:
            image_name (str): Logical image name as defined in the manifest.

        Returns:
            dict: Image entry with at least ``url`` and ``filename`` keys.

        Raises:
            KeywordException: If the image name is not found in the manifest.
        """
        manifest = self._load_manifest()
        images = manifest.get("images", {})

        if image_name not in images:
            available = ", ".join(images.keys())
            raise KeywordException(f"Image '{image_name}' not found in manifest '{self._manifest_path}'. " f"Available images: {available}")

        return images[image_name]

    def get_image_url(self, image_name: str) -> str:
        """Get the download URL for an image.

        Args:
            image_name (str): Logical image name.

        Returns:
            str: Full download URL.
        """
        return self.get_image_entry(image_name)["url"]

    def get_image_filename(self, image_name: str) -> str:
        """Get the filename for an image.

        Args:
            image_name (str): Logical image name.

        Returns:
            str: Image filename.
        """
        return self.get_image_entry(image_name)["filename"]

    def download_image(self, image_name: str, destination_dir: str) -> str:
        """Download a file by logical name from the manifest.

        Resolves the URL and filename from the manifest, then downloads
        the file to the specified directory on the remote host via wget.

        Args:
            image_name (str): Logical image name as defined in the manifest.
            destination_dir (str): Remote directory to download into.

        Returns:
            str: Absolute path to the downloaded file on the remote host.

        Raises:
            KeywordException: If the image name is not found or download fails.
        """
        entry = self.get_image_entry(image_name)
        url = entry["url"]
        filename = entry["filename"]
        destination_path = f"{destination_dir}/{filename}"

        get_logger().log_info(f"Downloading image '{image_name}' from {url}")
        WgetKeywords(self._ssh_connection).download_file(url, destination_path)
        get_logger().log_info(f"Image '{image_name}' downloaded to {destination_path}")

        return destination_path
