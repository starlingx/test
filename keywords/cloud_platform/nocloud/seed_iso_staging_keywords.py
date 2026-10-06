"""Keywords to stage a built seed ISO onto the SC HTTPS tree.

Copies a seed ISO from a source path (the automation working directory) to the
System Controller's HTTPS-served ISO tree so it can be fetched by RVMC. Kept as a
separate, single-purpose keyword from the seed builder: the builder produces the
ISO, this keyword only stages (copies) it.
"""

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords

# Staged seed ISO filename on the HTTPS tree.
SEED_ISO_NAME = "seed.iso"


class SeedIsoStagingKeywords(BaseKeyword):
    """Keywords to stage/unstage a seed ISO on the SC HTTPS-served ISO tree."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize SeedIsoStagingKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active System Controller.
        """
        self.ssh_connection = ssh_connection
        self.onsite_restore_config = ConfigurationManager.get_backup_restore_config().get_onsite_restore_config()
        self.file_keywords = FileKeywords(ssh_connection)

    def stage_seed_iso_to_https(self, subcloud_name: str, source_iso_path: str, software_version: str) -> str:
        """Copy a built seed ISO to the SC HTTPS-served ISO tree.

        Destination is
        '<www_iso_base_path>/<software_version>/nodes/<subcloud_name>/seed.iso'.
        The destination directory is created if needed and any stale ISO is removed
        before copying.

        Args:
            subcloud_name (str): Name of the target subcloud.
            source_iso_path (str): Path of the built seed ISO to copy from.
            software_version (str): Subcloud software version (destination is nested
                under this version).

        Returns:
            str: The destination server path of the staged seed ISO.
        """
        destination_path = self._get_staged_iso_path(subcloud_name, software_version)
        destination_dir = destination_path.rsplit("/", 1)[0]

        get_logger().log_info(f"Staging seed ISO {source_iso_path} -> {destination_path}")
        self.file_keywords.create_directory_with_sudo(destination_dir)
        if self.file_keywords.validate_file_exists_with_sudo(destination_path):
            self.file_keywords.delete_file(destination_path)

        self.file_keywords.copy_file(source_iso_path, destination_path, sudo=True)
        self.validate_success_return_code(self.ssh_connection)

        if not self.file_keywords.validate_file_exists_with_sudo(destination_path):
            raise FileNotFoundError(f"Seed ISO was not staged to {destination_path}")

        return destination_path

    def unstage_seed_iso(self, subcloud_name: str, software_version: str) -> None:
        """Remove a previously staged seed ISO from the SC HTTPS tree.

        Args:
            subcloud_name (str): Name of the target subcloud.
            software_version (str): Subcloud software version used to locate the ISO.
        """
        destination_path = self._get_staged_iso_path(subcloud_name, software_version)
        if self.file_keywords.validate_file_exists_with_sudo(destination_path):
            get_logger().log_info(f"Unstaging seed ISO: {destination_path}")
            self.file_keywords.delete_file(destination_path)

    def _get_staged_iso_path(self, subcloud_name: str, software_version: str) -> str:
        """Return the SC HTTPS-served path for the staged seed ISO.

        Args:
            subcloud_name (str): Name of the target subcloud.
            software_version (str): Subcloud software version.

        Returns:
            str: Absolute path
                '<www_iso_base_path>/<software_version>/nodes/<subcloud_name>/seed.iso'.
        """
        base = self.onsite_restore_config.get_www_iso_base_path()
        return f"{base}/{software_version}/nodes/{subcloud_name}/{SEED_ISO_NAME}"
