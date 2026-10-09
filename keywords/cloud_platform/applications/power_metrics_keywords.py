"""Shared power-metrics application and metrics keywords.

Provides reusable class-based keywords to install the power-metrics
application, wait for its telegraf and cadvisor pods to become ready, manage
its helm overrides, and fetch and validate the metrics it exposes on every lab
node, using existing framework keywords instead of raw SSH commands. Intended
to be reused by any test suite that needs power-metrics applied as a
precondition.

Application-level operations run against the active controller connection
passed as ``ssh_connection``. The metric validations are all-nodes assertions,
so they iterate the optional ``node_ssh_connections`` list and raise if it was
not supplied.
"""

from functools import partial

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry, validate_greater_than_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

POWER_METRICS_NAMESPACE = "power-metrics"
POWER_METRICS_LABEL = "power-metrics"
POWER_METRICS_LABEL_ASSIGN = "power-metrics=enabled"
TELEGRAF_POD_NAME = "telegraf"
CADVISOR_POD_NAME = "cadvisor"
CONTROLLER_PATH = "/home/sysadmin/"
YAML_LOCAL_PATH = "resources/cloud_platform/power_metrics/"
TELEGRAF_METRICS_ENDPOINT = "telegraf.power-metrics.svc.cluster.local:9273/metrics"
CADVISOR_METRICS_ENDPOINT = "cadvisor.power-metrics.svc.cluster.local/metrics"
CPU_FREQUENCY_METRIC = "powerstat_core_cpu_frequency_mhz"
VALIDATION_TIMEOUT_SECONDS = 30
VALIDATION_POLLING_SLEEP_SECONDS = 3


class PowerMetricsKeywords(BaseKeyword):
    """Keywords for power-metrics application setup and metrics validation."""

    def __init__(self, ssh_connection: SSHConnection, node_ssh_connections: list[SSHConnection] = None) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
            node_ssh_connections (list[SSHConnection]): One SSH connection per lab node.
                Optional; when omitted the connections are resolved from the lab config
                on first use by the metric validation keywords.
        """
        self.ssh_connection = ssh_connection
        self.node_ssh_connections = node_ssh_connections

    def get_app_name(self) -> str:
        """Get the power-metrics application name from the app config.

        Returns:
            str: The power-metrics application name.
        """
        return ConfigurationManager.get_app_config().get_power_metrics_app_name()

    def get_node_names(self) -> list[str]:
        """Get the lab node names that power-metrics runs on.

        Returns:
            list[str]: The host names of every node in the lab config.
        """
        return [node.get_name() for node in ConfigurationManager.get_lab_config().get_nodes()]

    def get_node_ssh_connections(self) -> list[SSHConnection]:
        """Get the per-node SSH connections used by the metric validations.

        Resolves one connection per lab node on first use and caches the result, so
        callers do not have to build and pass the list themselves.

        Returns:
            list[SSHConnection]: One SSH connection per lab node.
        """
        if not self.node_ssh_connections:
            self.node_ssh_connections = [LabConnectionKeywords().get_ssh_for_hostname(node_name) for node_name in self.get_node_names()]
        return self.node_ssh_connections

    def assign_power_metrics_labels(self) -> None:
        """Assign the power-metrics=enabled label to every node if not already present."""
        system_host_label_keywords = SystemHostLabelKeywords(self.ssh_connection)
        for node_name in self.get_node_names():
            if not system_host_label_keywords.get_system_host_label_list(node_name).get_label_value(POWER_METRICS_LABEL):
                get_logger().log_info(f"Assigning {POWER_METRICS_LABEL_ASSIGN} to node '{node_name}'")
                system_host_label_keywords.system_host_label_assign(node_name, POWER_METRICS_LABEL_ASSIGN)

    def ensure_power_metrics_applied(self) -> None:
        """Ensure power-metrics is labeled, uploaded, and applied.

        Idempotent: assigns node labels, uploads the tarball if missing, and
        applies the application if it is not already applied.
        """
        self.assign_power_metrics_labels()

        app_name = self.get_app_name()
        apply_keywords = SystemApplicationApplyKeywords(self.ssh_connection)
        if apply_keywords.is_already_applied(app_name):
            get_logger().log_info(f"{app_name} already applied, skipping upload and apply")
            return

        system_applications = SystemApplicationListKeywords(self.ssh_connection).get_system_application_list()
        if not system_applications.is_in_application_list(app_name):
            get_logger().log_info(f"Uploading {app_name} application")
            base_application_path = ConfigurationManager.get_app_config().get_base_application_path()
            upload_input = SystemApplicationUploadInput()
            upload_input.set_app_name(app_name)
            upload_input.set_tar_file_path(f"{base_application_path}{app_name}*.tgz")
            SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload(upload_input)

        get_logger().log_info(f"Applying {app_name} application")
        apply_keywords.system_application_apply(app_name)

    def is_power_metrics_already_applied(self) -> bool:
        """Check whether the power-metrics application is already in the applied state.

        Returns:
            bool: True if the application reports the applied state.
        """
        return SystemApplicationApplyKeywords(self.ssh_connection).is_already_applied(self.get_app_name())

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

    def wait_for_cadvisor_running(self, timeout: int = 300) -> None:
        """Wait for the cadvisor pods to reach Running status.

        Args:
            timeout (int): Maximum time to wait in seconds.
        """
        get_logger().log_info(f"Waiting for cadvisor pods to be Running (timeout={timeout}s)")
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(
            expected_status="Running",
            pod_names=[CADVISOR_POD_NAME],
            namespace=POWER_METRICS_NAMESPACE,
            timeout=timeout,
        )

    def get_telegraf_pod_count(self) -> int:
        """Get the number of telegraf pods in the power-metrics namespace.

        Returns:
            int: The number of pods whose name contains the telegraf pod name.
        """
        pods_output = KubectlGetPodsKeywords(self.ssh_connection).get_pods(namespace=POWER_METRICS_NAMESPACE)
        return len([pod for pod in pods_output.get_pods() if TELEGRAF_POD_NAME in pod.get_name()])

    def validate_telegraf_not_running(self, timeout: int = VALIDATION_TIMEOUT_SECONDS, polling_sleep_time: int = VALIDATION_POLLING_SLEEP_SECONDS) -> None:
        """Validate that no telegraf pods are running in the power-metrics namespace.

        Polls the pod count until it reaches zero, to allow the pods to terminate
        after a disabling override is applied.

        Args:
            timeout (int): Maximum time to wait in seconds for the pods to terminate.
            polling_sleep_time (int): Interval in seconds between pod count reads.
        """
        get_logger().log_info("Asserting telegraf pod is NOT running...")
        validate_equals_with_retry(
            self.get_telegraf_pod_count,
            0,
            "Telegraf pod should NOT be running after disable",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def apply_power_metrics(self) -> None:
        """Apply the power-metrics application.

        Used to re-apply the application after a helm override is uploaded, so tests
        do not need to hold the controller connection themselves.
        """
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(self.get_app_name())

    def upload_and_apply_helm_override(self, yaml_file_name: str, chart_name: str = "telegraf") -> None:
        """Upload a YAML override file to the controller and apply it as a helm override.

        Args:
            yaml_file_name (str): The override file name under the power_metrics resource folder.
            chart_name (str): The chart the override applies to.
        """
        get_logger().log_info(f"Uploading and applying helm override: {yaml_file_name}")
        yaml_file_local_path = get_stx_resource_path(YAML_LOCAL_PATH + yaml_file_name)
        yaml_file_remote_path = CONTROLLER_PATH + yaml_file_name
        FileKeywords(self.ssh_connection).upload_file(yaml_file_local_path, yaml_file_remote_path)
        SystemHelmOverrideKeywords(self.ssh_connection).update_helm_override(
            yaml_file=yaml_file_remote_path,
            app_name=self.get_app_name(),
            chart_name=chart_name,
            namespace=POWER_METRICS_NAMESPACE,
        )

    def delete_override_and_reapply(self, chart_name: str = "telegraf") -> None:
        """Delete the user helm override, reapply the application, and wait for telegraf pods.

        Args:
            chart_name (str): The chart whose override is deleted.
        """
        app_name = self.get_app_name()
        get_logger().log_info(f"Deleting helm override and reapplying {app_name}...")
        SystemHelmOverrideKeywords(self.ssh_connection).delete_system_helm_override(app_name, chart_name, POWER_METRICS_NAMESPACE)
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(app_name)
        self.wait_for_telegraf_running()

    def remove_power_metrics_labels(self) -> None:
        """Remove the power-metrics label from every lab node that still carries it.

        Mirrors ``assign_power_metrics_labels`` and skips nodes where the label is
        already absent, so the removal is safe to run more than once.
        """
        system_host_label_keywords = SystemHostLabelKeywords(self.ssh_connection)
        for node_name in self.get_node_names():
            if not system_host_label_keywords.get_system_host_label_list(node_name).get_label_value(POWER_METRICS_LABEL):
                get_logger().log_info(f"{POWER_METRICS_LABEL} label not present on node '{node_name}', skipping removal")
                continue
            get_logger().log_info(f"Removing {POWER_METRICS_LABEL} label from node '{node_name}'")
            system_host_label_keywords.system_host_label_remove(node_name, POWER_METRICS_LABEL)

    def remove_power_metrics(self) -> None:
        """Remove power-metrics labels and remove-and-delete the application.

        Removes the node labels first, then removes and deletes the application if
        it is still present in the application list. Does not close SSH
        connections; the caller owns connection lifecycle.
        """
        get_logger().log_teardown_step("Removing power-metrics labels from all nodes")
        self.remove_power_metrics_labels()

        app_name = self.get_app_name()
        get_logger().log_teardown_step(f"Verifying {app_name} is present before removal")
        system_applications = SystemApplicationListKeywords(self.ssh_connection).get_system_application_list()
        if not system_applications.is_in_application_list(app_name):
            get_logger().log_teardown_step(f"{app_name} not present, no need to teardown.")
            return

        get_logger().log_teardown_step(f"Removing and deleting {app_name} application")
        SystemApplicationRemoveKeywords(self.ssh_connection).system_application_remove_and_delete_app(app_name)

    def is_power_metrics_installed(self) -> bool:
        """Check whether the application is present in the system application list.

        Treats "present in the application list" as installed, in any state. An
        uploaded-but-not-applied application counts as installed, because
        ``remove_power_metrics`` leaves the application absent entirely (remove
        followed by delete).

        Returns:
            bool: True if the application is present in the application list.
        """
        return SystemApplicationListKeywords(self.ssh_connection).is_app_present(self.get_app_name())

    def validate_power_metrics_applied(self, timeout: int = 300) -> None:
        """Validate that the application reports the applied status.

        Args:
            timeout (int): Maximum time to wait in seconds for the applied status.
        """
        app_name = self.get_app_name()
        get_logger().log_info(f"Asserting {app_name} status is {SystemApplicationStatusEnum.APPLIED.value}")
        SystemApplicationListKeywords(self.ssh_connection).validate_app_status(app_name, SystemApplicationStatusEnum.APPLIED.value, timeout)

    def get_metrics(self, ssh_connection: SSHConnection, endpoint: str = TELEGRAF_METRICS_ENDPOINT, grep_pattern: str = None, max_lines: int = None) -> list:
        """Fetch metric lines from the given endpoint on a given node.

        Args:
            ssh_connection (SSHConnection): The node connection to curl from.
            endpoint (str): The metrics endpoint to query.
            grep_pattern (str): Optional pattern piped to grep on the node.
            max_lines (int): Optional line limit piped to head on the node.

        Returns:
            list: Metric lines, excluding blank lines and comment lines.
        """
        node_name = ssh_connection.get_name()
        cmd = f"curl -s {endpoint}"
        if grep_pattern:
            cmd += f" | grep {grep_pattern}"
        if max_lines:
            cmd += f" | head -n {max_lines}"
        get_logger().log_info(f"Fetching metrics from {endpoint} on node '{node_name}'")
        output = ssh_connection.send(cmd)
        results = [line for line in output if line.strip() and not line.startswith("#")]
        get_logger().log_info(f"Fetched {len(results)} metric line(s) from {endpoint} on node '{node_name}'")
        return results

    def filter_metrics(self, all_metrics: list, pattern: str) -> list:
        """Filter metric lines that contain the given pattern.

        Args:
            all_metrics (list): The metric lines to filter.
            pattern (str): The substring each returned line must contain.

        Returns:
            list: The metric lines containing the pattern.
        """
        return [line for line in all_metrics if pattern in line]

    def get_metric_match_count(self, ssh_connection: SSHConnection, metric: str, endpoint: str = TELEGRAF_METRICS_ENDPOINT, grep_pattern: str = None, max_lines: int = None) -> int:
        """Get the number of metric lines matching the given metric on a given node.

        Args:
            ssh_connection (SSHConnection): The node connection to curl from.
            metric (str): The substring each counted line must contain.
            endpoint (str): The metrics endpoint to query.
            grep_pattern (str): Optional pattern piped to grep on the node.
            max_lines (int): Optional line limit piped to head on the node.

        Returns:
            int: The number of metric lines containing the metric.
        """
        all_metrics = self.get_metrics(ssh_connection, endpoint, grep_pattern, max_lines)
        return len(self.filter_metrics(all_metrics, metric))

    def validate_metrics(self, metrics_list: list, context_msg: str, should_be_present: bool = True, endpoint: str = TELEGRAF_METRICS_ENDPOINT, grep_pattern: str = None, max_lines: int = None, timeout: int = VALIDATION_TIMEOUT_SECONDS, polling_sleep_time: int = VALIDATION_POLLING_SLEEP_SECONDS) -> None:
        """Validate whether every metric in the list is reported on every node.

        Polls each metric on each node until the expected presence is observed.
        Absence is polled the same way as presence, since metrics can take a moment
        to stop being reported after an override is applied.

        Args:
            metrics_list (list): The metric names to validate.
            context_msg (str): Message appended to each validation for traceability.
            should_be_present (bool): True to require at least one matching line per
                metric, False to require none.
            endpoint (str): The metrics endpoint to query.
            grep_pattern (str): Optional pattern piped to grep on the node.
            max_lines (int): Optional line limit piped to head on the node.
            timeout (int): Maximum time to wait in seconds for each metric to reach the
                expected presence.
            polling_sleep_time (int): Interval in seconds between metric reads.
        """
        expectation_msg = "PRESENT" if should_be_present else "ABSENT"
        get_logger().log_info(f"Asserting metrics {expectation_msg} on all nodes: {context_msg}")
        for ssh_connection in self.get_node_ssh_connections():
            for metric in metrics_list:
                get_metric_match_count = partial(self.get_metric_match_count, ssh_connection, metric, endpoint, grep_pattern, max_lines)
                validation_description = f"{metric} {context_msg}"
                if should_be_present:
                    validate_greater_than_with_retry(get_metric_match_count, 0, validation_description, timeout=timeout, polling_sleep_time=polling_sleep_time)
                else:
                    validate_equals_with_retry(get_metric_match_count, 0, validation_description, timeout=timeout, polling_sleep_time=polling_sleep_time)

    def get_cpu_id_match_count(self, ssh_connection: SSHConnection, cpu_id: str) -> int:
        """Get the number of cpu_frequency metric lines reported for a given CPU on a given node.

        Args:
            ssh_connection (SSHConnection): The node connection to curl from.
            cpu_id (str): The CPU identifier each counted line must report.

        Returns:
            int: The number of cpu_frequency metric lines for the CPU identifier.
        """
        all_metrics = self.get_metrics(ssh_connection)
        freq_metrics = self.filter_metrics(all_metrics, CPU_FREQUENCY_METRIC)
        return len([line for line in freq_metrics if f'cpu_id="{cpu_id}"' in line])

    def validate_cpu_ids(self, cpu_ids: list, context_msg: str, should_be_present: bool = True, timeout: int = VALIDATION_TIMEOUT_SECONDS, polling_sleep_time: int = VALIDATION_POLLING_SLEEP_SECONDS) -> None:
        """Validate whether cpu_frequency metrics are reported for every given CPU on every node.

        Polls each CPU identifier on each node until the expected presence is observed.
        Absence is polled the same way as presence, since metrics can take a moment to
        stop being reported after an override is applied.

        Args:
            cpu_ids (list): The CPU identifiers to validate.
            context_msg (str): Message appended to each validation for traceability.
            should_be_present (bool): True to require at least one matching line per CPU
                identifier, False to require none.
            timeout (int): Maximum time to wait in seconds for each CPU identifier to reach
                the expected presence.
            polling_sleep_time (int): Interval in seconds between metric reads.
        """
        expectation_msg = "PRESENT" if should_be_present else "ABSENT"
        get_logger().log_info(f"Asserting cpu_ids {cpu_ids} {expectation_msg} on all nodes: {context_msg}")
        for ssh_connection in self.get_node_ssh_connections():
            for cpu_id in cpu_ids:
                get_cpu_id_match_count = partial(self.get_cpu_id_match_count, ssh_connection, cpu_id)
                validation_description = f"cpu_id={cpu_id} {context_msg}"
                if should_be_present:
                    validate_greater_than_with_retry(get_cpu_id_match_count, 0, validation_description, timeout=timeout, polling_sleep_time=polling_sleep_time)
                else:
                    validate_equals_with_retry(get_cpu_id_match_count, 0, validation_description, timeout=timeout, polling_sleep_time=polling_sleep_time)
