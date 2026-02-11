from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter


class KubectlDeleteConfigmapKeywords(BaseKeyword):
    """Keywords for kubectl delete configmap operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize delete configmap keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)

    def delete_configmap(self, configmap_name: str, namespace: str, ignore_not_found: bool = False) -> None:
        """Delete configmap resource.

        Args:
            configmap_name (str): Name of the configmap to delete.
            namespace (str): Namespace where the configmap is deployed.
            ignore_not_found (bool): If True, adds --ignore-not-found=true flag. Defaults to False.
        """
        ignore_flag = " --ignore-not-found=true" if ignore_not_found else ""
        cmd = f"kubectl delete configmaps -n {namespace} {configmap_name}{ignore_flag}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
