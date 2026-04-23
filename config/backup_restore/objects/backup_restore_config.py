import json5


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

    def get_local_backup_base_path(self) -> str:
        """Getter for local backup base path.

        Returns:
            str: The base path for storing backup files locally.
        """
        return self.local_backup_base_path
