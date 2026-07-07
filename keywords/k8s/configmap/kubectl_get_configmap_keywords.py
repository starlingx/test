"""Keywords for kubectl get configmap operations."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.configmap.object.kubectl_get_configmap_output import KubectlGetConfigmapOutput
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter


class KubectlGetConfigmapKeywords(BaseKeyword):
    """Keywords for reading ConfigMap resources."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize get configmap keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)

    def get_configmap(self, configmap_name: str, namespace: str) -> KubectlGetConfigmapOutput:
        """Get a ConfigMap resource as a parsed object.

        Args:
            configmap_name (str): Name of the ConfigMap.
            namespace (str): Namespace where the ConfigMap exists.

        Returns:
            KubectlGetConfigmapOutput: Parsed output containing the ConfigMap object.
        """
        cmd = f"kubectl get configmap {configmap_name} -n {namespace} -o json"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetConfigmapOutput(output)
