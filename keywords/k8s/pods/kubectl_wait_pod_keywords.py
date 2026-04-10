"""Keywords for kubectl wait pod operations."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlWaitPodKeywords(K8sBaseKeyword):
    """Keywords for waiting on Kubernetes pod conditions."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize KubectlWaitPodKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def wait_for_pods_ready(self, label: str, namespace: str, timeout: int = 120) -> None:
        """Wait for pods matching a label to pass their readiness probes.

        Example usage::
            kubectl wait --for=condition=Ready pod -l kubevirt.io=virt-api -n kubevirt --timeout=120s

        Args:
            label (str): Label selector to match pods (e.g., 'kubevirt.io=virt-api').
            namespace (str): Namespace of the pods.
            timeout (int): Maximum time to wait in seconds. Defaults to 120.

        Raises:
            KeywordException: If pods do not become ready within the timeout.
        """
        get_logger().log_info(f"Waiting for pods with label '{label}' in namespace '{namespace}' to be ready")
        cmd = f"kubectl wait --for=condition=Ready pod -l {label} -n {namespace} --timeout={timeout}s"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
