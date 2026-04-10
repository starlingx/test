"""Keywords for waiting on Kubernetes custom resource conditions."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlWaitCrdKeywords(K8sBaseKeyword):
    """Keywords for waiting on CRD resource conditions."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize KubectlWaitCrdKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def wait_for_condition(self, resource: str, resource_name: str, condition: str, namespace: str, timeout: int = 120) -> None:
        """Wait for a custom resource to reach a specific condition.

        Example usage::

            kubectl -n kubevirt wait kv kubevirt --for condition=Available --timeout=120s

        Args:
            resource (str): Resource type short name (e.g., 'kv', 'deployment').
            resource_name (str): Name of the resource.
            condition (str): Condition to wait for (e.g., 'Available', 'Ready').
            namespace (str): Namespace of the resource.
            timeout (int): Maximum time to wait in seconds. Defaults to 120.
        """
        get_logger().log_info(f"Waiting for {resource}/{resource_name} in namespace '{namespace}' to reach condition '{condition}'")
        cmd = f"kubectl -n {namespace} wait {resource} {resource_name} --for condition={condition} --timeout={timeout}s"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
