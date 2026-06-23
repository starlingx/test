"""Keywords for listing Kubernetes Lease resources."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.lease.object.kubectl_get_lease_output import KubectlGetLeaseOutput


class KubectlGetLeaseKeywords(K8sBaseKeyword):
    """Keywords for listing Kubernetes Lease resources."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize KubectlGetLeaseKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_leases(self, namespace: str) -> KubectlGetLeaseOutput:
        """Get leases in a namespace.

        Args:
            namespace (str): Namespace to list leases in.

        Returns:
            KubectlGetLeaseOutput: Parsed output containing all Lease objects.
        """
        cmd = f"kubectl get lease -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetLeaseOutput(output)
