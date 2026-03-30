from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.systeminventory.object.kubectl_systeminventory_output import KubectlSystemInventoryOutput


class KubectlGetSystemInventoryKeywords(K8sBaseKeyword):
    """
    Keywords for kubectl SystemInventory operations.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_system_inventory_json(self, sysinv_name: str, namespace: str = "default") -> KubectlSystemInventoryOutput:
        """
        Get a SystemInventory resource as JSON.

        Args:
            sysinv_name (str): Name of the SystemInventory resource
            namespace (str): Kubernetes namespace. Defaults to "default"

        Returns:
            KubectlSystemInventoryOutput: Parsed SystemInventory output object
        """
        get_logger().log_info(f"Getting SystemInventory '{sysinv_name}' in namespace '{namespace}'")

        cmd = f"kubectl get systeminventory {sysinv_name} -n {namespace} -o json"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return KubectlSystemInventoryOutput(output, sysinv_name)

    def system_inventory_exists(self, sysinv_name: str, namespace: str = "default") -> bool:
        """
        Check if a SystemInventory resource exists.

        Args:
            sysinv_name (str): Name of the SystemInventory resource
            namespace (str): Kubernetes namespace. Defaults to "default"

        Returns:
            bool: True if SystemInventory exists, False otherwise
        """
        cmd = f"kubectl get systeminventory {sysinv_name} -n {namespace}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        return self.ssh_connection.get_return_code() == 0
