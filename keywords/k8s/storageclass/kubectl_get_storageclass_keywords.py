"""Kubernetes StorageClass kubectl keywords."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.storageclass.object.kubectl_get_storageclass_output import KubectlGetStorageclassOutput


class KubectlGetStorageclassKeywords(K8sBaseKeyword):
    """Keywords for 'kubectl get sc' operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize StorageClass keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
                If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_storageclasses(self) -> KubectlGetStorageclassOutput:
        """Get all StorageClasses via 'kubectl get sc -o yaml'.

        Returns:
            KubectlGetStorageclassOutput: Parsed StorageClass collection
                with classification metadata.
        """
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get sc -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetStorageclassOutput(output)

    def select_storage_class(self, preferred_storage_class: str = None) -> str:
        """Discover available StorageClasses and select the best one.

        Selection priority:
        1. The preferred StorageClass if provided and exists in the cluster.
        2. The cluster's default StorageClass.
        3. The first available StorageClass.

        Args:
            preferred_storage_class (str, optional): Preferred StorageClass name.
                If None, skips preference check and uses default or first available.

        Returns:
            str: The selected StorageClass name.

        Raises:
            ValueError: If no StorageClasses are available.
        """
        sc_output = self.get_storageclasses()
        all_scs = sc_output.get_storageclasses()

        if not all_scs:
            raise ValueError("No StorageClasses available in the cluster")

        sc_names = [sc.get_name() for sc in all_scs]
        get_logger().log_info(f"Available StorageClasses: {sc_names}")

        if preferred_storage_class and preferred_storage_class in sc_names:
            return preferred_storage_class

        default_sc = sc_output.get_default_storageclass()
        if default_sc:
            get_logger().log_info(f"Preferred '{preferred_storage_class}' not found, using default: {default_sc.get_name()}")
            return default_sc.get_name()

        get_logger().log_info(f"No preferred or default StorageClass, using first available: {sc_names[0]}")
        return sc_names[0]
