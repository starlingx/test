"""Keywords for kubectl wait pod operations."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.k8s.daemonsets.kubectl_get_daemonsets_keywords import KubectlGetDaemonsetsKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


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

    def wait_for_all_pods_ready(self, namespace: str, timeout: int = 300) -> None:
        """Wait for all pods in a namespace to pass their readiness probes.

        Example usage::
            kubectl wait --for=condition=Ready pod --all -n default --timeout=300s

        Args:
            namespace (str): Namespace of the pods.
            timeout (int): Maximum time to wait in seconds. Defaults to 300.

        Raises:
            KeywordException: If pods do not become ready within the timeout.
        """
        get_logger().log_info(f"Waiting for all pods in namespace '{namespace}' to be ready")
        cmd = f"kubectl wait --for=condition=Ready pod --all -n {namespace} --timeout={timeout}s"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def wait_for_daemonset_ready(self, namespace: str, daemonset_name: str | None = None, timeout: int = 300, polling_sleep_time: int = 5) -> dict[str, dict]:
        """Wait for the current DaemonSet rollout on every independently eligible node.

        Check observed generation, rollout counts, ownership, revision consistency
        and every declared container. Unsupported scheduling fails explicitly.
        Refresh scheduling and pod evidence on every poll.
        Existing pod-only waits retain their behavior.

        Args:
            namespace (str): Namespace containing the DaemonSet and its pods.
            daemonset_name (str | None): DaemonSet name; None requires exactly one in the namespace.
            timeout (int): Maximum polling duration in seconds.
            polling_sleep_time (int): Delay between readiness observations in seconds.

        Returns:
            dict[str, dict]: Current ready pods indexed by eligible node name.
        """

        def observe() -> ValidationResponse:
            workload = KubectlGetDaemonsetsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_daemonset_workload(namespace, daemonset_name)
            pods = KubectlGetPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_pods_json(namespace=namespace, label=workload.get_label_selector()).get_pod_records()
            ready_pods = workload.get_ready_pods(pods)
            return ValidationResponse(bool(ready_pods), ready_pods)

        return validate_equals_with_retry(observe, True, "DaemonSet pods ready on every eligible node", timeout=timeout, polling_sleep_time=polling_sleep_time)
