from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class KubectlRestartPodKeywords(K8sBaseKeyword):
    """
    Keywords for restarting a Kubernetes pod and waiting for it to be ready again.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def restart_pod_by_label(self, label: str, namespace: str, timeout: int = 600, polling_sleep_time: int = 10) -> str:
        """
        Restart a pod selected by label and wait until it is Running and Ready again.

        Deletes the Running pod matching the label, which forces a reschedule.
        For a StatefulSet the pod is recreated with the same name; between the
        delete returning and the replacement being scheduled there is a window
        where no pod matches the label, during which "kubectl wait" fails
        immediately with "no matching resources" rather than waiting. This
        polls for the pod to come back Running and Ready instead, which
        tolerates that gap.

        Args:
            label (str): Label selector identifying the pod to restart.
            namespace (str): The namespace of the pod.
            timeout (int): Maximum seconds to wait for the pod to be ready. Defaults to 600.
            polling_sleep_time (int): Seconds between readiness polls. Defaults to 10.

        Returns:
            str: The name of the pod that was restarted.

        Raises:
            KeywordException: If no Running pod matches the label.
        """
        pods_kw = KubectlGetPodsKeywords(self.ssh_connection)
        pods = pods_kw.get_pods(namespace=namespace, label=label).get_pods()
        running = [pod.get_name() for pod in pods if pod.get_status() == "Running"]
        if not running:
            raise KeywordException(f"No Running pod found with label '{label}' in namespace '{namespace}'")
        target_pod = running[0]
        get_logger().log_info(f"Restarting pod '{target_pod}' (label '{label}')")
        KubectlDeletePodsKeywords(self.ssh_connection).delete_pod(target_pod, namespace=namespace)

        def _pod_ready() -> bool:
            current = pods_kw.get_pods(namespace=namespace, label=label).get_pods()
            matching = [pod for pod in current if pod.get_name() == target_pod]
            if not matching:
                return False
            pod = matching[0]
            return pod.get_status() == "Running" and pod.is_ready()

        validate_equals_with_retry(
            _pod_ready,
            True,
            f"Pod '{target_pod}' is Running and Ready again",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )
        get_logger().log_info(f"Pod '{target_pod}' is Ready again")
        return target_pod
