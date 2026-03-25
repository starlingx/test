from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteImagePolicyKeywords(K8sBaseKeyword):
    """Keywords for deleting Kubernetes image policies."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize kubectl delete image policy keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_all_imagepolicies(self) -> None:
        """Delete all image policies in the cluster."""
        self.ssh_connection.send(self.k8s_config.export("kubectl delete imagepolicy --all --ignore-not-found=true"))
        self.validate_success_return_code(self.ssh_connection)

    def delete_all_clusterimagepolicies(self) -> None:
        """Delete all cluster image policies in the cluster."""
        self.ssh_connection.send(self.k8s_config.export("kubectl delete clusterimagepolicy --all --ignore-not-found=true"))
        self.validate_success_return_code(self.ssh_connection)
