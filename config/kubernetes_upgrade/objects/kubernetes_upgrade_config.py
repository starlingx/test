import json5


class KubernetesUpgradeConfig:
    """
    Class to hold configuration for Kubernetes upgrade operations.
    """

    def __init__(self, config: str):
        """
        Load and parse the Kubernetes upgrade config file.

        Args:
            config (str): Path to the JSON5 Kubernetes upgrade config file.

        Raises:
            FileNotFoundError: If the config file cannot be found.
        """
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the kubernetes upgrade config file: {config}")
            raise

        kubernetes_upgrade_dict = json5.load(json_data)
        self.k8_target_version = kubernetes_upgrade_dict["k8_target_version"]
        self.subcloud_group = kubernetes_upgrade_dict.get("subcloud_group", "None")
        self.subcloud_name = kubernetes_upgrade_dict.get("subcloud_name", "None")

    def get_k8_target_version(self) -> str:
        """
        Getter for the Kubernetes version to upgrade to.

        Returns:
            str: The target Kubernetes version.
        """
        return self.k8_target_version

    def get_subcloud_group(self) -> str:
        """
        Getter for the subcloud group name.

        Returns:
            str: The subcloud group name.
        """
        return self.subcloud_group

    def get_subcloud_name(self) -> str:
        """
        Getter for the subcloud name.

        Returns:
            str: The subcloud name.
        """
        return self.subcloud_name
