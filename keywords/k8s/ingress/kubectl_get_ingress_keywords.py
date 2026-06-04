"""Keywords for the ``kubectl get ingress`` CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.ingress.object.kubectl_get_ingress_output import KubectlGetIngressOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetIngressKeywords(K8sBaseKeyword):
    """
    Class for kubectl get ingress keywords.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_ingress(self, ingress_name: str, namespace: str = None) -> KubectlGetIngressOutput:
        """
        Get a single ingress resource by name.

        Args:
            ingress_name (str): The name of the ingress.
            namespace (str): The namespace of the ingress. If None, uses the current context.

        Returns:
            KubectlGetIngressOutput: The ingress output object.
        """
        cmd = f"kubectl get ingress {ingress_name}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        kubectl_get_ingress_output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetIngressOutput(kubectl_get_ingress_output)

    def get_ingresses(self, namespace: str = None) -> KubectlGetIngressOutput:
        """
        Get all ingress resources from the specified namespace.

        Args:
            namespace (str): The namespace to query. If None, uses the current context.

        Returns:
            KubectlGetIngressOutput: The ingress output object.
        """
        cmd = "kubectl get ingress"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        kubectl_get_ingress_output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetIngressOutput(kubectl_get_ingress_output)
