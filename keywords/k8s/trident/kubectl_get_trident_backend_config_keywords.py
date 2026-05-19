"""Keywords for kubectl get tridentbackendconfig operations."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.trident.object.kubectl_get_trident_backend_config_output import KubectlGetTridentBackendConfigOutput


class KubectlGetTridentBackendConfigKeywords(K8sBaseKeyword):
    """Keywords for retrieving TridentBackendConfig resources."""

    TRIDENT_NAMESPACE = "trident"

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize KubectlGetTridentBackendConfigKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_trident_backend_configs(self, namespace: str = None) -> KubectlGetTridentBackendConfigOutput:
        """Get all TridentBackendConfigs in the specified namespace.

        Args:
            namespace (str, optional): Namespace to query. Defaults to 'trident'.

        Returns:
            KubectlGetTridentBackendConfigOutput: Parsed TBC list.
        """
        ns = namespace or self.TRIDENT_NAMESPACE
        cmd = self.k8s_config.export(f"kubectl get tridentbackendconfig -n {ns} -o json")
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetTridentBackendConfigOutput(output)
