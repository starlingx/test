import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals, validate_greater_than
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

POWER_METRICS_NAMESPACE = "power-metrics"
CONTROLLER_PATH = "/home/sysadmin/"
YAML_LOCAL_PATH = "resources/cloud_platform/power_metrics/"


class HelperPowerMetrics:
    """Helper class for testing power-metrics application.

    Provides setup/teardown lifecycle methods that install and remove the
    power-metrics application, and reusable test operations for validating
    metrics collection, helm overrides, and telegraf pod status.
    """

    def __init__(self) -> None:
        self.logger = get_logger()
        self.ssh_connection: SSHConnection
        self.app_name: str
        self.node_ssh_connections: list[SSHConnection] = []
        self.helm: SystemHelmOverrideKeywords
        self.kubectl_pods: KubectlGetPodsKeywords

    # ============================================================================
    # Setup and Teardown Methods
    # ============================================================================

    def setup_method(self):
        """Connect to the lab and ensure power-metrics is installed (uploaded, applied, labeled)."""
        app_config = ConfigurationManager.get_app_config()
        self.app_name = app_config.get_power_metrics_app_name()
        lab_config = ConfigurationManager.get_lab_config()

        self.logger.log_setup_step(f"Connecting to lab: {lab_config.get_lab_name()}")
        self.ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        self.helm = SystemHelmOverrideKeywords(self.ssh_connection)
        self.kubectl_pods = KubectlGetPodsKeywords(self.ssh_connection)
        self.node_ssh_connections = [
            LabConnectionKeywords().get_ssh_for_hostname(node.get_name())
            for node in lab_config.get_nodes()
        ]

        apply_keywords = SystemApplicationApplyKeywords(self.ssh_connection)
        if apply_keywords.is_already_applied(self.app_name):
            self.logger.log_info(f"{self.app_name} is already applied, tearing down.")
            self.teardown_method()

        self.logger.log_setup_step(f"Installing {self.app_name} application")
        base_path = app_config.get_base_application_path()
        system_host_label_keywords = SystemHostLabelKeywords(self.ssh_connection)

        self.logger.log_setup_step("Assigning power-metrics=enabled labels to all nodes")
        for node in lab_config.get_nodes():
            if not system_host_label_keywords.get_system_host_label_list(node.get_name()).get_label_value("power-metrics"):
                system_host_label_keywords.system_host_label_assign(node.get_name(), "power-metrics=enabled")

        system_applications = SystemApplicationListKeywords(self.ssh_connection).get_system_application_list()
        if not system_applications.is_in_application_list(self.app_name):
            self.logger.log_setup_step(f"Uploading {self.app_name} application")
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(self.app_name)
            system_application_upload_input.set_tar_file_path(f"{base_path}{self.app_name}*.tgz")
            SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload(system_application_upload_input)

        self.logger.log_setup_step(f"Applying {self.app_name} application")
        apply_keywords.system_application_apply(self.app_name)

    def teardown_method(self):
        """Remove and delete power-metrics application and remove labels from all nodes."""
        app_config = ConfigurationManager.get_app_config()
        power_metrics_name = app_config.get_power_metrics_app_name()
        lab_config = ConfigurationManager.get_lab_config()
        system_host_label_keywords = SystemHostLabelKeywords(self.ssh_connection)

        self.logger.log_teardown_step("Removing power-metrics labels from all nodes")
        for node in lab_config.get_nodes():
            system_host_label_keywords.system_host_label_remove(node.get_name(), "power-metrics")

        self.logger.log_teardown_step(f"Verifying {power_metrics_name} is present before removal")
        system_applications = SystemApplicationListKeywords(self.ssh_connection).get_system_application_list()
        if not system_applications.is_in_application_list(power_metrics_name):
            self.logger.log_teardown_step(f"{power_metrics_name} not present, no need to teardown.")
            SSHConnectionManager.remove_all()
            return

        self.logger.log_teardown_step(f"Removing {power_metrics_name} application")
        system_application_remove_input = SystemApplicationRemoveInput()
        system_application_remove_input.set_app_name(power_metrics_name)
        system_application_remove_input.set_force_removal(False)
        system_application_output = SystemApplicationRemoveKeywords(self.ssh_connection).system_application_remove(system_application_remove_input)
        validate_equals(system_application_output.get_system_application_object().get_status(), SystemApplicationStatusEnum.UPLOADED.value, "Application removal status validation")

        self.logger.log_teardown_step(f"Deleting {power_metrics_name} application")
        system_application_delete_input = SystemApplicationDeleteInput()
        system_application_delete_input.set_app_name(power_metrics_name)
        system_application_delete_input.set_force_deletion(False)
        delete_msg = SystemApplicationDeleteKeywords(self.ssh_connection).get_system_application_delete(system_application_delete_input)
        validate_equals(delete_msg, f"Application {power_metrics_name} deleted.\n", "Application deletion message validation")

        self.logger.log_teardown_step("Disconnecting from lab")
        SSHConnectionManager.remove_all()

    # ============================================================================
    # Reusable Helper Methods
    # ============================================================================

    def fetch_all_metrics(self, ssh_connection: SSHConnection, endpoint: str = "telegraf.power-metrics.svc.cluster.local:9273/metrics", grep_pattern: str = None, max_lines: int = None) -> list:
        """Fetch metrics from the given endpoint on a given node."""
        cmd = f"curl -s {endpoint}"
        if grep_pattern:
            cmd += f" | grep {grep_pattern}"
        if max_lines:
            cmd += f" | head -n {max_lines}"
        output = ssh_connection.send(cmd)
        results = [line for line in output if line.strip() and not line.startswith("#")]
        self.logger.log_info(f"Fetched {len(results)} metric line(s) from {endpoint}")
        return results

    def filter_metrics(self, all_metrics: list, pattern: str) -> list:
        """Filter metric lines that contain the given pattern."""
        return [line for line in all_metrics if pattern in line]

    def wait_for_telegraf_running(self, timeout=300):
        """Wait for telegraf pods to reach Running status."""
        self.logger.log_info(f"Waiting for telegraf pods to be Running (timeout={timeout}s)...")
        self.kubectl_pods.wait_for_pods_to_reach_status(
            expected_status="Running",
            pod_names=["telegraf"],
            namespace=POWER_METRICS_NAMESPACE,
            timeout=timeout,
        )

    def wait_for_cadvisor_running(self, timeout=300):
        """Wait for cadvisor pods to reach Running status."""
        self.logger.log_info(f"Waiting for cadvisor pods to be Running (timeout={timeout}s)...")
        self.kubectl_pods.wait_for_pods_to_reach_status(
            expected_status="Running",
            pod_names=["cadvisor"],
            namespace=POWER_METRICS_NAMESPACE,
            timeout=timeout,
        )

    def assert_metrics_present_on_all_nodes(self, metrics_list: list, context_msg: str, endpoint: str = "telegraf.power-metrics.svc.cluster.local:9273/metrics", grep_pattern: str = None, max_lines: int = None):
        """Validate that all metrics in the list are present on every node."""
        self.logger.log_info(f"Asserting metrics PRESENT on all nodes: {context_msg}")
        for ssh_connection in self.node_ssh_connections:
            for metric in metrics_list:
                for attempt in range(4):
                    all_metrics = self.fetch_all_metrics(ssh_connection, endpoint, grep_pattern, max_lines)
                    matches = self.filter_metrics(all_metrics, metric)
                    if len(matches) > 0:
                        break
                    self.logger.log_info(f"No matches for {metric}, retrying ({attempt + 1}/3) after 3s...")
                    time.sleep(3)
                validate_greater_than(len(matches), 0, f"{metric} {context_msg}")

    def assert_metrics_absent_on_all_nodes(self, metrics_list: list, context_msg: str, endpoint: str = "telegraf.power-metrics.svc.cluster.local:9273/metrics", grep_pattern: str = None, max_lines: int = None):
        """Validate that all metrics in the list are absent on every node."""
        self.logger.log_info(f"Asserting metrics ABSENT on all nodes: {context_msg}")
        for ssh_connection in self.node_ssh_connections:
            all_metrics = self.fetch_all_metrics(ssh_connection, endpoint, grep_pattern, max_lines)
            for metric in metrics_list:
                matches = self.filter_metrics(all_metrics, metric)
                validate_equals(len(matches), 0, f"{metric} {context_msg}")

    def assert_cpu_ids_present_on_all_nodes(self, cpu_ids: list, context_msg: str):
        """Validate that the given cpu_ids are present in cpu_frequency metrics on every node."""
        self.logger.log_info(f"Asserting cpu_ids {cpu_ids} PRESENT on all nodes: {context_msg}")
        metric_name = "powerstat_core_cpu_frequency_mhz"
        for ssh_connection in self.node_ssh_connections:
            for cpu_id in cpu_ids:
                for attempt in range(4):
                    all_metrics = self.fetch_all_metrics(ssh_connection)
                    freq_metrics = self.filter_metrics(all_metrics, metric_name)
                    matches = [line for line in freq_metrics if f'cpu_id="{cpu_id}"' in line]
                    if len(matches) > 0:
                        break
                    self.logger.log_info(f"No matches for cpu_id={cpu_id}, retrying ({attempt + 1}/3) after 3s...")
                    time.sleep(3)
                validate_greater_than(len(matches), 0, f"cpu_id={cpu_id} {context_msg}")

    def assert_cpu_ids_absent_on_all_nodes(self, cpu_ids: list, context_msg: str):
        """Validate that the given cpu_ids are absent from cpu_frequency metrics on every node."""
        self.logger.log_info(f"Asserting cpu_ids {cpu_ids} ABSENT on all nodes: {context_msg}")
        metric_name = "powerstat_core_cpu_frequency_mhz"
        for ssh_connection in self.node_ssh_connections:
            for cpu_id in cpu_ids:
                for attempt in range(4):
                    all_metrics = self.fetch_all_metrics(ssh_connection)
                    freq_metrics = self.filter_metrics(all_metrics, metric_name)
                    matches = [line for line in freq_metrics if f'cpu_id="{cpu_id}"' in line]
                    if len(matches) == 0:
                        break
                    self.logger.log_info(f"cpu_id={cpu_id} still present, retrying ({attempt + 1}/3) after 3s...")
                    time.sleep(3)
                validate_equals(len(matches), 0, f"cpu_id={cpu_id} {context_msg}")

    def assert_telegraf_not_running(self):
        """Validate that no telegraf pods are running."""
        self.logger.log_info("Asserting telegraf pod is NOT running...")
        pods_output = self.kubectl_pods.get_pods(namespace=POWER_METRICS_NAMESPACE)
        telegraf_pods = [p for p in pods_output.get_pods() if "telegraf" in p.get_name()]
        validate_equals(len(telegraf_pods), 0, "Telegraf pod should NOT be running after disable")

    def upload_and_apply_helm_override(self, yaml_file_name: str, chart_name: str = "telegraf"):
        """Upload a YAML override file to the controller and apply it as a helm override."""
        self.logger.log_info(f"Uploading and applying helm override: {yaml_file_name}")
        yaml_file_local_path = get_stx_resource_path(YAML_LOCAL_PATH + yaml_file_name)
        yaml_file_remote_path = CONTROLLER_PATH + yaml_file_name
        FileKeywords(self.ssh_connection).upload_file(yaml_file_local_path, yaml_file_remote_path)
        self.helm.update_helm_override(
            yaml_file=yaml_file_remote_path,
            app_name=self.app_name,
            chart_name=chart_name,
            namespace=POWER_METRICS_NAMESPACE,
        )

    def delete_override_and_reapply(self, chart_name: str = "telegraf"):
        """Delete the user helm override, reapply the application, and wait for telegraf pods."""
        self.logger.log_info(f"Deleting helm override and reapplying {self.app_name}...")
        self.helm.delete_system_helm_override(self.app_name, chart_name, POWER_METRICS_NAMESPACE)
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(self.app_name)
        self.wait_for_telegraf_running()

