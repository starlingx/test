import json5

from config.lab.objects.credentials import Credentials


class StorageConfig:
    """Class to hold configuration for Storage tests."""

    def __init__(self, config: str):
        """Initialize storage configuration.

        Args:
            config (str): Path to configuration file.
        """
        with open(config) as json_data:
            storage_dict = json5.load(json_data)

        # iSCSI credentials configuration
        iscsi_config = storage_dict.get("iscsi_credentials", {})
        self.iscsi_credentials = Credentials(iscsi_config)

    def get_iscsi_credentials(self) -> Credentials:
        """Getter for iSCSI credentials.

        Returns:
            Credentials: The iSCSI credentials object.
        """
        return self.iscsi_credentials
