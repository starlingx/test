"""Keywords for listing Kubernetes Custom Resource Definitions (CRDs)."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.crd.object.kubectl_get_crd_output import KubectlGetCrdOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetCrdKeywords(K8sBaseKeyword):
    """Keywords for listing Kubernetes Custom Resource Definitions (CRDs)."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize KubectlGetCrdKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_crds(self) -> KubectlGetCrdOutput:
        """Get the list of registered CRDs.

        Returns:
            KubectlGetCrdOutput: Parsed output containing all CRD objects.
        """
        cmd = "kubectl get crd"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetCrdOutput(output)
