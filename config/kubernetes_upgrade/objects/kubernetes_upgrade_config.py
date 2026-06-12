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

        # Strategy creation arguments
        self.sw_mgr_controller_apply_type = kubernetes_upgrade_dict.get("sw_mgr_controller_apply_type", "None")
        self.sw_mgr_storage_apply_type = kubernetes_upgrade_dict.get("sw_mgr_storage_apply_type", "None")
        self.sw_mgr_worker_apply_type = kubernetes_upgrade_dict.get("sw_mgr_worker_apply_type", "None")
        self.sw_mgr_instance_action = kubernetes_upgrade_dict.get("sw_mgr_instance_action", "None")
        self.sw_mgr_alarm_restrictions = kubernetes_upgrade_dict.get("sw_mgr_alarm_restrictions", "None")
        self.sw_mgr_max_parallel_worker_hosts = kubernetes_upgrade_dict.get("sw_mgr_max_parallel_worker_hosts", "None")

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

    def get_controller_apply_type(self) -> str:
        """
        Getter for the controller apply type.

        Returns:
            str: The controller apply type (serial, ignore, or None if not set).
        """
        return self.sw_mgr_controller_apply_type

    def get_storage_apply_type(self) -> str:
        """
        Getter for the storage apply type.

        Returns:
            str: The storage apply type (serial, ignore, or None if not set).
        """
        return self.sw_mgr_storage_apply_type

    def get_worker_apply_type(self) -> str:
        """
        Getter for the worker apply type.

        Returns:
            str: The worker apply type (serial, parallel, ignore, or None if not set).
        """
        return self.sw_mgr_worker_apply_type

    def get_instance_action(self) -> str:
        """
        Getter for the instance action during upgrade.

        Returns:
            str: The instance action (stop-start, migrate, or None if not set).
        """
        return self.sw_mgr_instance_action

    def get_alarm_restrictions(self) -> str:
        """
        Getter for the alarm restrictions policy.

        Returns:
            str: The alarm restrictions (strict, relaxed, or None if not set).
        """
        return self.sw_mgr_alarm_restrictions

    def get_max_parallel_worker_hosts(self) -> str:
        """
        Getter for the maximum number of parallel worker hosts.

        Returns:
            str: The maximum parallel worker hosts (2-10, or None if not set).
        """
        return self.sw_mgr_max_parallel_worker_hosts

    def resolve_target_version(self, available_versions: list) -> str:
        """
        Resolve the target Kubernetes version for upgrade.

        If a target version is configured, returns it directly.
        Otherwise, selects the highest available version by semantic version sorting.

        Args:
            available_versions (list): List of available Kubernetes version strings (e.g. ["v1.28.4", "v1.29.1"]).

        Returns:
            str: The resolved target Kubernetes version.
        """
        target = self.k8_target_version
        if target and target != "None":
            return target
        return sorted(available_versions, key=lambda v: list(map(int, v.lstrip("v").split("."))))[-1]
