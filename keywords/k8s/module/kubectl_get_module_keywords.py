from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter
from keywords.k8s.module.object.kubectl_get_module_output import KubectlGetModuleOutput


class KubectlGetModuleKeywords(BaseKeyword):
    """Keywords for kubectl module operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize module keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)

    def get_modules(self, namespace: str) -> KubectlGetModuleOutput:
        """Get modules in namespace.

        Args:
            namespace (str): Namespace where modules are deployed.

        Returns:
            KubectlGetModuleOutput: Object containing parsed module output.
        """
        cmd = f"kubectl get modules.kmm.sigs.x-k8s.io -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetModuleOutput(output)

    def get_module(self, module_name: str, namespace: str) -> str:
        """Get module resource.

        Args:
            module_name (str): Name of the module.
            namespace (str): Namespace where the module is deployed.

        Returns:
            str: Output of kubectl get command for the module.
        """
        cmd = f"kubectl get modules.kmm.sigs.x-k8s.io -n {namespace} {module_name}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output

    def is_module_present(self, module_name: str, namespace: str) -> bool:
        """Check if module resource exists.

        Args:
            module_name (str): Name of the module.
            namespace (str): Namespace where the module is deployed.

        Returns:
            bool: True if module exists, False otherwise.
        """
        modules_output = self.get_modules(namespace)
        return modules_output.module_exists(module_name)
