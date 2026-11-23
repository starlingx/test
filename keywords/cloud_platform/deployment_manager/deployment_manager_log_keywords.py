import re

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_not_none_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.k8s.crd.kubectl_dm_resources_keywords import RECONCILE_POLLING_INTERVAL, RECONCILE_TIMEOUT
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_logs_keywords import KubectlLogsKeywords

DEPLOYMENT_MANAGER_NAMESPACE = "platform-deployment-manager"


class DeploymentManagerLogKeywords(BaseKeyword):
    """
    This class reads the logs of the platform-deployment-manager pod.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def get_controller_utc_time(self) -> str:
        """Get the current UTC time of the controller, in the format used by 'kubectl logs --since-time'.

        The time comes from the controller, not from the machine running the test, so the two clocks
        cannot drift apart.

        Returns:
            str: Controller UTC time, e.g. "2026-11-14T00:05:53Z".
        """
        output = self.ssh_connection.send("date -u +%Y-%m-%dT%H:%M:%SZ")
        self.validate_success_return_code(self.ssh_connection)
        return "".join(output).strip()

    def get_deployment_manager_pod_name(self) -> str:
        """Get the name of the platform-deployment-manager pod.

        Returns:
            str: Pod name.

        Raises:
            KeywordException: If there is no platform-deployment-manager pod.
        """
        pods = KubectlGetPodsKeywords(self.ssh_connection).get_pods(namespace=DEPLOYMENT_MANAGER_NAMESPACE).get_pods()
        names = [pod.get_name() for pod in pods if DEPLOYMENT_MANAGER_NAMESPACE in pod.get_name()]
        if not names:
            raise KeywordException(f"No pod with '{DEPLOYMENT_MANAGER_NAMESPACE}' in its name was found in the {DEPLOYMENT_MANAGER_NAMESPACE} namespace.")
        return names[0]

    def get_logs_since(self, since_time: str) -> str:
        """Get the platform-deployment-manager pod logs written after a given time.

        Args:
            since_time (str): RFC3339 time, e.g. "2026-11-14T00:05:53Z".

        Returns:
            str: Pod logs.
        """
        pod_name = self.get_deployment_manager_pod_name()
        return KubectlLogsKeywords(self.ssh_connection).get_logs(pod_name, namespace=DEPLOYMENT_MANAGER_NAMESPACE, since_time=since_time)

    def wait_for_log_line(self, pattern: str, start_time: str, description: str) -> str:
        """Wait until a regular expression matches the platform-deployment-manager logs written after start_time.

        Args:
            pattern (str): Regular expression to search for.
            start_time (str): RFC3339 time to read the logs from.
            description (str): Description of the check, for logging.

        Returns:
            str: The text that matched.
        """
        match = validate_not_none_with_retry(lambda: re.search(pattern, self.get_logs_since(start_time)), description, timeout=RECONCILE_TIMEOUT, polling_sleep_time=RECONCILE_POLLING_INTERVAL)
        get_logger().log_info(f"Regex output for {pattern} : {match.group()}")
        return match.group()
