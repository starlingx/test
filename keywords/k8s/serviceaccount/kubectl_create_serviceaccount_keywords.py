from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCreateServiceAccountKeywords(K8sBaseKeyword):
    """Kubectl keywords for creating service accounts."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def create_serviceaccount(self, serviceaccount_name: str, namespace: str = None) -> None:
        """Create a Kubernetes service account.

        Args:
            serviceaccount_name (str): Name of the service account to create.
            namespace (str, optional): Namespace for the service account.
        """
        cmd = f"kubectl create serviceaccount {serviceaccount_name}"
        if namespace:
            cmd += f" -n {namespace}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"ServiceAccount '{serviceaccount_name}' created in namespace '{namespace or 'default'}'")
