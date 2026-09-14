from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords


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

    def create_namespace_if_absent(self, name: str) -> None:
        """Create a k8s namespace, skipping the create if it already exists.

        Safe to call repeatedly: it checks the current namespaces first and only
        creates the namespace when it is missing.

        Args:
            name (str): Namespace name.
        """
        namespaces = KubectlGetNamespacesKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_namespaces()
        if namespaces.is_namespace(name):
            get_logger().log_info(f"Namespace '{name}' already exists - skipping create")
            return
        get_logger().log_info(f"Creating namespace '{name}'")
        self.create_namespaces(name)
