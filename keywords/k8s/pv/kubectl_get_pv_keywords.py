"""Keywords for kubectl get pv operations."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter
from keywords.k8s.pv.object.kubectl_get_pv_output import KubectlGetPvOutput


class KubectlGetPvKeywords(BaseKeyword):
    """Keywords for kubectl get pv commands."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)

    def get_pvs(self) -> KubectlGetPvOutput:
        """Get all PersistentVolumes in the cluster.

        Returns:
            KubectlGetPvOutput: Parsed output containing all PVs.
        """
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get pv"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetPvOutput(output)
