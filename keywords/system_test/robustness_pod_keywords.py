import re
import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class RobustnessPodKeywords:
    """Keyword helpers for pod-state bookkeeping during robustness tests.

    Robustness operations (lock/unlock, reboot, power cycle, swact) churn the
    workload, so the tests need to capture a Running-pod baseline, wait for that
    baseline to be restored afterwards, and clean up the stale errored pods a
    respun workload leaves behind. These helpers encapsulate that pod-state logic
    so the test cases stay focused on the operation under test.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize the RobustnessPodKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_running_pod_count(self) -> int:
        """Get the cluster-wide count of pods currently in Running status.

        Returns:
            int: Number of pods in Running status across all namespaces.
        """
        pods = KubectlGetPodsKeywords(self.ssh_connection).get_pods_all_namespaces().get_pods()
        return len([pod for pod in pods if pod.get_status() == "Running"])

    def get_pod_owner_prefix(self, pod_name: str) -> str:
        """Derive a pod's owner prefix by stripping the ReplicaSet/pod hash suffixes.

        Kubernetes names pods as '<owner>-<replicaset-hash>-<pod-hash>' (Deployments)
        or '<owner>-<ordinal>' (StatefulSets/DaemonSets). Stripping the trailing
        hash-like segments groups a pod with its respun siblings.

        Args:
            pod_name (str): Full pod name.

        Returns:
            str: The owner prefix used to match a pod against its replacements.
        """
        parts = pod_name.split("-")
        # Drop trailing segments that look like generated hashes/ordinals so that an
        # errored pod and its healthy replacement resolve to the same prefix.
        while len(parts) > 1 and re.fullmatch(r"[0-9a-z]{1,10}", parts[-1]):
            parts.pop()
        return "-".join(parts)

    def cleanup_leftover_error_pods(self) -> list:
        """Delete errored pods that are stale leftovers of a respun workload.

        An errored pod is considered a stale leftover only when another pod sharing
        the same owner prefix and namespace is already Running or Completed (i.e. the
        workload has been respun and the errored instance is dead residue). Errored
        pods with no healthy sibling are left untouched so genuine failures stay visible.

        Returns:
            list: List of "namespace/pod" identifiers that were deleted.
        """
        pods = KubectlGetPodsKeywords(self.ssh_connection).get_pods_all_namespaces().get_pods()

        healthy_prefixes = set()
        for pod in pods:
            if pod.get_status() in ("Running", "Succeeded", "Completed"):
                healthy_prefixes.add((pod.get_namespace(), self.get_pod_owner_prefix(pod.get_name())))

        deleted = []
        for pod in pods:
            if pod.get_status() not in ("Error", "Failed"):
                continue
            key = (pod.get_namespace(), self.get_pod_owner_prefix(pod.get_name()))
            if key in healthy_prefixes:
                self.ssh_connection.send(source_openrc(f"kubectl delete pod {pod.get_name()} -n {pod.get_namespace()} --ignore-not-found=true"))
                deleted.append(f"{pod.get_namespace()}/{pod.get_name()}")
                get_logger().log_info(f"Deleted stale errored pod (respun): {pod.get_namespace()}/{pod.get_name()}")
            else:
                get_logger().log_warning(f"Errored pod kept (no healthy sibling, possible real failure): {pod.get_namespace()}/{pod.get_name()}")

        return deleted

    def wait_for_running_pod_count_restored(self, expected_count: int, timeout: int = 3600, check_interval: int = 15) -> int:
        """Wait until the cluster-wide Running pod count is restored to a baseline.

        Treats recovery as successful when at least as many pods are Running as before
        the operation, tolerating stale errored leftovers. Errored pods are logged each
        cycle so they stay visible.

        Args:
            expected_count (int): Baseline count of Running pods captured before the operation.
            timeout (int): Maximum time to wait in seconds.
            check_interval (int): Seconds between polls.

        Returns:
            int: The Running pod count observed once the baseline was restored.

        Raises:
            KeywordException: If the baseline is not restored within timeout.
        """
        end_time = time.time() + timeout
        running_count = 0
        while time.time() < end_time:
            pods = KubectlGetPodsKeywords(self.ssh_connection).get_pods_all_namespaces().get_pods()
            running_count = len([pod for pod in pods if pod.get_status() == "Running"])
            error_pods = [f"{pod.get_namespace()}/{pod.get_name()}" for pod in pods if pod.get_status() in ("Error", "Failed")]
            get_logger().log_info(f"Running pods: {running_count}/{expected_count} (errored leftovers: {len(error_pods)})")
            if error_pods:
                get_logger().log_info(f"Errored pods present (ignored if respun): {error_pods}")
            if running_count >= expected_count:
                return running_count
            time.sleep(check_interval)

        raise KeywordException(f"Running pod count {running_count} did not reach baseline {expected_count} within {timeout}s")
