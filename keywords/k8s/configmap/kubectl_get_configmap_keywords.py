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

    def get_configmap_names(self, namespace: str) -> list[str]:
        """Return the names of all ConfigMaps in a namespace.

        Args:
            namespace (str): Namespace to list ConfigMaps from.

        Returns:
            list[str]: ConfigMap names in the namespace.
        """
        cmd = f"kubectl get configmap -n {namespace} -o jsonpath='{{.items[*].metadata.name}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        text = "".join(output) if isinstance(output, list) else output
        return text.split()

    def has_configmap_matching(self, namespace: str, marker: str) -> bool:
        """Return whether any ConfigMap name in a namespace contains a marker.

        Args:
            namespace (str): Namespace to search.
            marker (str): Substring to match against ConfigMap names.

        Returns:
            bool: True if at least one ConfigMap name contains the marker.
        """
        return any(marker in name for name in self.get_configmap_names(namespace))
