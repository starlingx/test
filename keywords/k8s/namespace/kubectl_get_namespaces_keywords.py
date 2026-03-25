from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.namespace.object.kubectl_get_namespaces_output import KubectlGetNamespacesOutput


class KubectlGetNamespacesKeywords(K8sBaseKeyword):
    """
    Class for 'kubectl get ns' keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_namespaces(self) -> KubectlGetNamespacesOutput:
        """Get the available k8s namespaces.

        Returns:
            KubectlGetNamespacesOutput: Parsed namespaces output.
        """
        kubectl_get_namespaces_output = self.ssh_connection.send(self.k8s_config.export("kubectl get ns"))
        self.validate_success_return_code(self.ssh_connection)
        namespaces_list_output = KubectlGetNamespacesOutput(kubectl_get_namespaces_output)

        return namespaces_list_output

    def get_namespaces_by_label(self, label: str) -> KubectlGetNamespacesOutput:
        """Get the available k8s namespaces for a given label.

        Args:
            label (str): The label selector.

        Returns:
            KubectlGetNamespacesOutput: Parsed namespaces output.
        """
        kubectl_get_namespaces_output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get ns -l={label}"))
        self.validate_success_return_code(self.ssh_connection)
        namespaces_list_output = KubectlGetNamespacesOutput(kubectl_get_namespaces_output)

        return namespaces_list_output
