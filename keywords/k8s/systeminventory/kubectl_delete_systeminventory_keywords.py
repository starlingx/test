from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteSystemInventoryKeywords(K8sBaseKeyword):
    """
    Keywords for deleting SystemInventory resources.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_system_inventory(self, sysinv_name: str, namespace: str) -> str:
        """
        Deletes the specified SystemInventory resource in the given namespace.

        Args:
            sysinv_name (str): The name of the SystemInventory to delete.
            namespace (str): The namespace where the SystemInventory is located.

        Returns:
            str: The output from the kubectl delete command.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl delete -n {namespace} systeminventory {sysinv_name}"))
        self.validate_success_return_code(self.ssh_connection)
        return output
