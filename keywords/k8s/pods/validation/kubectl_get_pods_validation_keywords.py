import time

from pytest import fail

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class KubectlPodValidationKeywords(BaseKeyword):
    """
    Class for 'kubectl pod' validation keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
        """
        self.ssh_connection = ssh_connection

    def validate_kube_system_pods_status(self):
        """
        This function will validate that the kube_system pods are in the expected state.

        - 'audit-', 'init-' and 'secret-observer-cron-job-' pods should be COMPLETED
        - Everything else should be RUNNING and READY
        """
        timeout = time.time() + 300
        is_validation_success = False

        # Retry the validation until we succeed or timeout.
        while time.time() < timeout and not is_validation_success:

            get_logger().log_info("Attempt to validate that kube-system pods are in the expected state.")
            get_pods_output = KubectlGetPodsKeywords(self.ssh_connection).get_pods("kube-system")
            is_validation_success = True

            for pod in get_pods_output.get_pods():

                # 'audit-', 'init-' and 'secret-observer-cron-job-' pods should be COMPLETED
                if "audit-" in pod.get_name() or "init-" in pod.get_name() or "secret-observer-cron-job-" in pod.get_name():
                    if pod.get_status() != "Completed":
                        is_validation_success = False
                        get_logger().log_error(f"Pod {pod.get_name()} in wrong status. Expected: 'Completed', Observed: '{pod.get_status()}'")

                # Other pods should be RUNNING.
                else:
                    if pod.get_status() != "Running":
                        is_validation_success = False
                        get_logger().log_error(f"Pod {pod.get_name()} in wrong status. Expected: 'Running', Observed: '{pod.get_status()}'")

                    # Validate READY state only for Running pods
                    if not pod.is_ready():
                        is_validation_success = False
                        get_logger().log_error(f"Pod {pod.get_name()} not ready. READY: '{pod.get_ready()}'")

            # Retry logging
            if not is_validation_success and time.time() + 2 < timeout:
                get_logger().log_error("Validation failed - Retry again in 5 seconds")
                time.sleep(5)

        if is_validation_success:
            get_logger().log_info("Validation Successful: kube-system pods are in the expected state.")
        else:
            fail("Validation of kube-system failed and timed out.")
