"""Kubernetes StorageClass kubectl keywords."""

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
