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

        # Storage credentials configuration
        credentials_config = storage_dict.get("credentials", {"user_name": "", "password": ""})
        self.credentials = Credentials(credentials_config)

        # Storage network configuration
        storage_network_config = storage_dict.get("storage_network", {})
        self.storage_network_ip_address = storage_network_config.get("ip_address", "")
        self.storage_network_interface_name = storage_network_config.get("interface_name", "")

        # Storage array configuration (lab specific, must not be committed to the repo)
        storage_array_config = storage_dict.get("storage_array", {})
        self.storage_array_id = storage_array_config.get("array_id", "")
        self.storage_array_endpoint = storage_array_config.get("endpoint", "")
        self.storage_array_nas_name = storage_array_config.get("nas_name", "")

    def get_credentials(self) -> Credentials:
        """Getter for storage credentials.

        Returns:
            Credentials: The storage credentials object.
        """
        return self.credentials

    def get_storage_network_ip_address(self) -> str:
        """Getter for storage network IP address with CIDR notation.

        Returns:
            str: The storage network IP address (e.g. '10.10.10.253/24').
        """
        return self.storage_network_ip_address

    def get_storage_network_interface_name(self) -> str:
        """Getter for storage network interface name.

        Returns:
            str: The network interface name (e.g. 'enp81s...').
        """
        return self.storage_network_interface_name

    def get_storage_array_id(self) -> str:
        """Getter for the storage array global ID.

        Returns:
            str: The storage array ID used as arrayID/globalID in the CSI overrides.
        """
        return self.storage_array_id

    def get_storage_array_endpoint(self) -> str:
        """Getter for the storage array REST API endpoint.

        Returns:
            str: The storage array endpoint (e.g. 'https://10.10.10.10/api/rest').
        """
        return self.storage_array_endpoint

    def get_storage_array_nas_name(self) -> str:
        """Getter for the storage array NAS server name.

        Returns:
            str: The NAS server name used by the NFS storage class (e.g. 'NAS1').
        """
        return self.storage_array_nas_name
