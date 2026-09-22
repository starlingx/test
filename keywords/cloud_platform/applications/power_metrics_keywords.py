"""Shared power-metrics application setup keywords.

Provides reusable class-based keywords to install the power-metrics application
and wait for its telegraf pods to become ready, using existing framework
keywords instead of raw SSH commands. Intended to be reused by any test suite
that needs power-metrics applied as a precondition.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

POWER_METRICS_NAMESPACE = "power-metrics"
POWER_METRICS_LABEL = "power-metrics"
POWER_METRICS_LABEL_ASSIGN = "power-metrics=enabled"
TELEGRAF_POD_NAME = "telegraf"


class PowerMetricsKeywords(BaseKeyword):
    """Keywords for shared power-metrics application setup operations."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def assign_power_metrics_labels(self, node_names: list[str]) -> None:
        """Assign the power-metrics=enabled label to every given node if not already present.

        Args:
            node_names (list[str]): The host names to label.
        """
        system_host_label_keywords = SystemHostLabelKeywords(self.ssh_connection)
        for node_name in node_names:
            if not system_host_label_keywords.get_system_host_label_list(node_name).get_label_value(POWER_METRICS_LABEL):
                get_logger().log_info(f"Assigning {POWER_METRICS_LABEL_ASSIGN} to node '{node_name}'")
                system_host_label_keywords.system_host_label_assign(node_name, POWER_METRICS_LABEL_ASSIGN)

    def ensure_power_metrics_applied(self, app_name: str, base_application_path: str, node_names: list[str]) -> None:
        """Ensure power-metrics is labeled, uploaded, and applied.

        Idempotent: assigns node labels, uploads the tarball if missing, and
        applies the application if it is not already applied.

        Args:
            app_name (str): The power-metrics application name.
            base_application_path (str): The base path where application tarballs are stored.
            node_names (list[str]): The host names to label with power-metrics=enabled.
        """
        self.assign_power_metrics_labels(node_names)

        apply_keywords = SystemApplicationApplyKeywords(self.ssh_connection)
        if apply_keywords.is_already_applied(app_name):
            get_logger().log_info(f"{app_name} already applied, skipping upload and apply")
            return

        system_applications = SystemApplicationListKeywords(self.ssh_connection).get_system_application_list()
        if not system_applications.is_in_application_list(app_name):
            get_logger().log_info(f"Uploading {app_name} application")
            upload_input = SystemApplicationUploadInput()
            upload_input.set_app_name(app_name)
            upload_input.set_tar_file_path(f"{base_application_path}{app_name}*.tgz")
            SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload(upload_input)

        get_logger().log_info(f"Applying {app_name} application")
        apply_keywords.system_application_apply(app_name)

    def wait_for_telegraf_running(self, timeout: int = 300) -> None:
        """Wait for the telegraf pods to reach Running status.

        Args:
            timeout (int): Maximum time to wait in seconds.
        """
        get_logger().log_info(f"Waiting for telegraf pods to be Running (timeout={timeout}s)")
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(
            expected_status="Running",
            pod_names=[TELEGRAF_POD_NAME],
            namespace=POWER_METRICS_NAMESPACE,
            timeout=timeout,
        )
