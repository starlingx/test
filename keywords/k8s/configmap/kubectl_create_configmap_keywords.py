"""Keywords for kubectl create configmap operations."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter


class KubectlCreateConfigmapKeywords(BaseKeyword):
    """Keywords for creating ConfigMap resources."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize create configmap keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)

    def create_configmap_from_dir(self, configmap_name: str, source_dir: str, namespace: str) -> None:
        """Create or update a ConfigMap from all files in a directory using server-side apply.

        Renders the ConfigMap with a client-side dry-run and pipes it into
        'kubectl apply --server-side'. Server-side apply avoids the 262KB
        last-applied-configuration annotation limit that client-side apply
        hits with large file collections.

        Args:
            configmap_name (str): Name of the ConfigMap.
            source_dir (str): Directory whose files become ConfigMap entries.
            namespace (str): Namespace where the ConfigMap is created.
        """
        cmd = f"kubectl create configmap {configmap_name} --from-file={source_dir} -n {namespace} --dry-run=client -o yaml | kubectl apply --server-side -f -"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
