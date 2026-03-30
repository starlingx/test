from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCreateNamespacesKeywords(K8sBaseKeyword):
    """
    Class for 'kubectl create ns' keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def create_namespaces(self, name: str) -> None:
        """Create a k8s namespace.

        Args:
            name (str): Namespace name.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl create ns {name}"))
        self.validate_success_return_code(self.ssh_connection)
