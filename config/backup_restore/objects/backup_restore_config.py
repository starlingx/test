"""Backup and restore configuration module.

Loads the backup_restore JSON5 configuration and exposes its nested sections
(local backup path, onsite restore, and local-site GRUB factory restore).
"""

import json5

from config.backup_restore.objects.factory_restore_grub_config import FactoryRestoreGrubConfig
from config.backup_restore.objects.onsite_restore_config import OnsiteRestoreConfig


class BackupRestoreConfig:
    """Class to hold configuration for Backup and Restore tests."""

    def __init__(self, config: str):
        """Initialize backup restore configuration.

        Args:
            config (str): Path to configuration file.
        """
        with open(config) as json_data:
            br_dict = json5.load(json_data)

        self.local_backup_base_path = br_dict.get("local_backup_base_path", "/tmp/bnr")
        self.onsite_restore = OnsiteRestoreConfig(br_dict.get("onsite_restore", {}))
        self.factory_restore_grub = FactoryRestoreGrubConfig(br_dict.get("factory_restore_grub", {}))

    def get_local_backup_base_path(self) -> str:
        """Getter for local backup base path.

        Returns:
            str: The base path for storing backup files locally.
        """
        return self.local_backup_base_path

    def get_onsite_restore_config(self) -> OnsiteRestoreConfig:
        """Getter for the onsite restore (without reinstall) configuration.

        Returns:
            OnsiteRestoreConfig: The nested onsite restore configuration.
        """
        return self.onsite_restore

    def get_factory_restore_grub_config(self) -> FactoryRestoreGrubConfig:
        """Getter for the local-site GRUB factory-restore configuration.

        Returns:
            FactoryRestoreGrubConfig: The nested factory-restore-grub config.
        """
        return self.factory_restore_grub
