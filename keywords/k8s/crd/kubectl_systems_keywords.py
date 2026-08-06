"""Keywords for 'kubectl get systems' CRD resource."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.crd.object.kubectl_systems_output import KubectlSystemsOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlSystemsKeywords(K8sBaseKeyword):
    """Keywords for getting Deployment Manager systems CRD resources."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_systems(self, namespace: str = "deployment") -> KubectlSystemsOutput:
        """Get all systems from the deployment namespace.

        Args:
            namespace (str): Namespace to query. Defaults to "deployment".

        Returns:
            KubectlSystemsOutput: Parsed output of 'kubectl get systems' command.
        """
        cmd = f"kubectl get systems -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlSystemsOutput(output)
