from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter


class KubectlDeleteModuleKeywords(BaseKeyword):
    """Keywords for kubectl delete module operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize delete module keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)

    def delete_module(self, module_name: str, namespace: str, ignore_not_found: bool = False) -> None:
        """Delete module resource.

        Args:
            module_name (str): Name of the module to delete.
            namespace (str): Namespace where the module is deployed.
            ignore_not_found (bool): If True, adds --ignore-not-found=true flag. Defaults to False.
        """
        ignore_flag = " --ignore-not-found=true" if ignore_not_found else ""
        cmd = f"kubectl delete modules.kmm.sigs.x-k8s.io -n {namespace} {module_name}{ignore_flag}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
