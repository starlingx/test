from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.objects.deployment_assets_network_object import DeploymentAssetsNetworkObject


class DeploymentAssetsNetworkOutput:
    """
    Represents the parsed network configuration from a deployment assets YAML file.
    """

    def __init__(self, lines: list[str], key_prefix: str):
        """
        Constructor

        Args:
            lines (list[str]): Lines read from the YAML file.
            key_prefix (str): Key prefix to match (e.g., 'admin', 'management').
        """
        self.network_object = DeploymentAssetsNetworkObject()

        required_keys = [
            f"{key_prefix}_start_address",
            f"{key_prefix}_end_address",
            f"{key_prefix}_gateway_address",
            f"{key_prefix}_subnet",
        ]
        found_keys = []

        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line.startswith(f"{key_prefix}_") or ":" not in line:
                continue

            key, value = line.split(":", 1)
            value = value.strip().strip("\"'")

            if key == f"{key_prefix}_start_address":
                self.network_object.set_start_address(value)
                found_keys.append(key)
            elif key == f"{key_prefix}_end_address":
                self.network_object.set_end_address(value)
                found_keys.append(key)
            elif key == f"{key_prefix}_gateway_address":
                self.network_object.set_gateway_address(value)
                found_keys.append(key)
            elif key == f"{key_prefix}_subnet":
                if "/" in value:
                    self.network_object.set_subnet(value.split("/")[0])
                    self.network_object.set_subnet_prefix(value.split("/")[1])
                else:
                    self.network_object.set_subnet(value)
                found_keys.append(key)
            elif key == f"{key_prefix}_subnet_prefix":
                self.network_object.set_subnet_prefix(value)

        missing = [k for k in required_keys if k not in found_keys]
        if missing:
            raise KeywordException(f"Missing required network keys for prefix '{key_prefix}': {missing}")

    def get_network_object(self) -> DeploymentAssetsNetworkObject:
        """
        Returns the parsed DeploymentAssetsNetworkObject.

        Returns:
            DeploymentAssetsNetworkObject: the parsed network configuration object.
        """
        return self.network_object
