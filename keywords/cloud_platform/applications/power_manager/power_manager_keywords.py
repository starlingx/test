"""Reusable keywords for the kubernetes-power-manager application test cases."""

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class PowerManagerKeywords(BaseKeyword):
    """Reusable keywords for kubernetes-power-manager test cases.

    Centralizes the domain logic shared across the kubernetes-power-manager test
    cases: detecting host support, verifying pods and CStates custom resources,
    managing the power-management label, and cleaning up the environment.
    """

    # Namespace where the kubernetes-power-manager pods are deployed.
    NAMESPACE = "intel-power"
    # Label required on the hosts for the kubernetes-power-manager application.
    MANAGEMENT_LABEL = "power-management=enabled"
    # Label key used when removing the label from the hosts.
    MANAGEMENT_LABEL_KEY = "power-management"
    # CStates custom resource (power.intel.com/v1), one per power-managed host and named after it.
    # It is rendered by the kubernetes-power-manager Helm chart when the app is (re)applied.
    # CSTATES_RESOURCE_TYPE is the kubectl resource name; CSTATES_KIND is the Kind used in messages.
    CSTATES_RESOURCE_TYPE = "cstates"
    CSTATES_KIND = "CStates"
    # Alarm raised when a configuration change requires the app to be reapplied.
    REAPPLY_ALARM_ID = "750.006"
    # Alarm raised while an application is being applied or reapplied, and its entity for this app.
    APPLY_IN_PROGRESS_ALARM_ID = "750.004"
    APP_ENTITY_ID = "k8s_application=kubernetes-power-manager"
    # Seconds to wait for the reapply alarm to be raised (short polling so a brief alarm is not missed).
    REAPPLY_ALARM_RAISE_TIMEOUT = 300
    REAPPLY_ALARM_RAISE_POLLING = 5
    # Seconds to wait for the reapply alarm to clear and for the app to return to 'applied'.
    REAPPLY_ALARM_CLEAR_TIMEOUT = 900
    REAPPLY_ALARM_CLEAR_POLLING = 30
    APP_APPLIED_TIMEOUT = 600

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def has_pstate_support(self) -> bool:
        """Check whether the host supports P-state (CPU frequency scaling) management.

        The host is P-state capable when the cpu0 cpufreq directory exists, the scaling driver
        is intel_pstate, intel_pstate is in 'active' mode, and both the 'performance' and
        'powersave' governors are available. A missing sysfs path or failed command means
        the host is not capable.

        Returns:
            bool: True if the host is P-state capable, False otherwise.
        """
        cpufreq_dir = "/sys/devices/system/cpu/cpu0/cpufreq"
        cpufreq_listing = self._read_sysfs(f"ls {cpufreq_dir}/")
        if not cpufreq_listing or "No such file" in cpufreq_listing:
            return False
        if self._read_sysfs(f"cat {cpufreq_dir}/scaling_driver") != "intel_pstate":
            return False
        if self._read_sysfs("cat /sys/devices/system/cpu/intel_pstate/status") != "active":
            return False
        governors = self._read_sysfs(f"cat {cpufreq_dir}/scaling_available_governors").split()
        return "performance" in governors and "powersave" in governors

    def has_cstate_support(self) -> bool:
        """Check whether the host supports C-state (CPU idle state) management.

        The host is C-state capable when the cpuidle driver is intel_idle and the cpu0
        idle states include POLL, C1, C1E and C6. A missing sysfs path or failed command
        means the host is not capable.

        Returns:
            bool: True if the host is C-state capable, False otherwise.
        """
        if self._read_sysfs("cat /sys/devices/system/cpu/cpuidle/current_driver") != "intel_idle":
            return False
        names_output = self._read_sysfs("grep . /sys/devices/system/cpu/cpu0/cpuidle/state*/name")
        state_names = {line.split(":")[-1].strip() for line in names_output.splitlines()}
        return {"POLL", "C1", "C1E", "C6"}.issubset(state_names)

    def _read_sysfs(self, command: str) -> str:
        """Run a read-only command and return its stripped output as a single string.

        Args:
            command (str): The command to run on the host.

        Returns:
            str: The command output (stderr included), stripped of surrounding whitespace.
        """
        output = self.ssh_connection.send(f"{command} 2>&1")
        text = "".join(output) if isinstance(output, list) else output
        return text.strip() if text else ""

    def wait_for_pods_running(self) -> None:
        """Wait for all kubernetes-power-manager pods to reach the Running status.

        Raises:
            KeywordException: If the pods do not reach Running within the timeout.
        """
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace=self.NAMESPACE)

    def wait_for_pods_deleted(self, timeout: int = 300, poll_interval: int = 15) -> None:
        """Wait for all pods in the kubernetes-power-manager namespace to be deleted.

        Args:
            timeout (int): Maximum time in seconds to wait. Defaults to 300.
            poll_interval (int): Time in seconds between checks. Defaults to 15.

        Raises:
            TimeoutError: If pods still exist after the timeout.
        """
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_be_deleted(self.NAMESPACE, poll_interval=poll_interval, timeout=timeout)

    def is_namespace_empty(self) -> bool:
        """Check whether the power manager namespace has no resources.

        Returns:
            bool: True if 'kubectl get all' reports no resources in the namespace.
        """
        return KubectlGetResourceKeywords(self.ssh_connection).is_namespace_empty(self.NAMESPACE)

    def is_reapply_alarm_present(self) -> bool:
        """Check whether the kubernetes-power-manager reapply alarm (750.006) is raised.

        Returns:
            bool: True if alarm 750.006 is currently present, False otherwise.
        """
        return AlarmListKeywords(self.ssh_connection).is_alarm_present(self.REAPPLY_ALARM_ID)

    def is_reapply_observed(self) -> bool:
        """Check whether a reapply of kubernetes-power-manager is required or in progress.

        Alarm 750.006 (reapply required) can be raised and cleared while the label command is
        still running, because sysinv starts the reapply right away. Alarm 750.004 (apply in
        progress) raised for this application is therefore also accepted as evidence. The alarm
        list is read once per call.

        Returns:
            bool: True if alarm 750.006, or alarm 750.004 for kubernetes-power-manager, is present.
        """
        for alarm in AlarmListKeywords(self.ssh_connection).alarm_list():
            if alarm.get_alarm_id() == self.REAPPLY_ALARM_ID:
                return True
            if alarm.get_alarm_id() == self.APPLY_IN_PROGRESS_ALARM_ID and self.APP_ENTITY_ID in alarm.get_entity_id():
                return True
        return False

    def wait_for_auto_reapply(self, app_name: str) -> None:
        """Wait for the application to be automatically reapplied after a configuration change.

        An absent alarm is not enough to prove a reapply happened: right after the change the
        alarm may not have been raised yet and the app is still 'applied'. So this keyword first
        waits for alarm 750.006 (reapply required) or 750.004 (apply in progress) to be raised,
        then for both to clear, and finally for the app to be back in the 'applied' state.

        Args:
            app_name (str): Name of the application that is expected to be reapplied.

        Raises:
            TimeoutError: If no reapply alarm is raised, the alarms do not clear, or the app does not return to 'applied' within the timeouts.
        """
        alarms = f"{self.REAPPLY_ALARM_ID}/{self.APPLY_IN_PROGRESS_ALARM_ID}"
        validate_equals_with_retry(
            function_to_execute=self.is_reapply_observed,
            expected_value=True,
            validation_description=f"Alarm {alarms} (kubernetes-power-manager reapply required or in progress) should be raised after the configuration change",
            timeout=self.REAPPLY_ALARM_RAISE_TIMEOUT,
            polling_sleep_time=self.REAPPLY_ALARM_RAISE_POLLING,
        )
        validate_equals_with_retry(
            function_to_execute=self.is_reapply_observed,
            expected_value=False,
            validation_description=f"Alarm {alarms} (kubernetes-power-manager reapply required or in progress) should clear automatically",
            timeout=self.REAPPLY_ALARM_CLEAR_TIMEOUT,
            polling_sleep_time=self.REAPPLY_ALARM_CLEAR_POLLING,
        )
        SystemApplicationListKeywords(self.ssh_connection).validate_app_status(app_name, SystemApplicationStatusEnum.APPLIED.value, timeout=self.APP_APPLIED_TIMEOUT, polling_sleep_time=self.REAPPLY_ALARM_CLEAR_POLLING)

    def get_cstate_names(self) -> list[str]:
        """Get the names of all CStates custom resources in the power manager namespace.

        An empty namespace yields an empty list. Any kubectl failure (connection error,
        missing CRD, RBAC) raises instead of being read as "no CStates".

        Returns:
            list[str]: Names of the CStates custom resources.

        Raises:
            Exception: If the kubectl command returns a non-zero exit code.
        """
        cmd = f"kubectl get {self.CSTATES_RESOURCE_TYPE} -n {self.NAMESPACE} -o jsonpath='{{.items[*].metadata.name}}'"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        text = "".join(output) if isinstance(output, list) else output
        return text.split() if text else []

    def is_cstate_present(self, host_name: str) -> bool:
        """Check whether a CStates custom resource exists for a given host.

        Args:
            host_name (str): The host to check.

        Returns:
            bool: True if a CStates custom resource exists for the host, False otherwise.

        Raises:
            Exception: If the CStates list cannot be retrieved.
        """
        return host_name in self.get_cstate_names()

    def assign_management_label_to_hosts(self, host_names: list[str]) -> None:
        """Assign the power-management=enabled label to the given hosts (with overwrite).

        Args:
            host_names (list[str]): Names of the hosts to label.
        """
        host_label_keywords = SystemHostLabelKeywords(self.ssh_connection)
        for host_name in host_names:
            host_label_keywords.system_host_label_assign(host_name, self.MANAGEMENT_LABEL, overwrite=True)

    def remove_management_label_from_all_hosts(self) -> None:
        """Remove the power-management label from every host where it is present (idempotent)."""
        SystemHostLabelKeywords(self.ssh_connection).remove_labels_from_all_hosts([self.MANAGEMENT_LABEL_KEY])

    def cleanup_environment(self, nfd_name: str, power_manager_name: str) -> None:
        """Remove and delete kubernetes-power-manager and its node-feature-discovery dependency.

        Each application is removed and deleted only when it is present in the
        system application list: kubernetes-power-manager first, then its
        node-feature-discovery dependency. The power-management label is removed last.

        Args:
            nfd_name (str): node-feature-discovery application name (dependency).
            power_manager_name (str): kubernetes-power-manager application name.
        """
        # Remove and delete each application; cleanup_app_if_present logs and skips when the app is absent.
        remove_keywords = SystemApplicationRemoveKeywords(self.ssh_connection)
        for app_name in (power_manager_name, nfd_name):
            remove_keywords.cleanup_app_if_present(app_name, force_removal=True, force_deletion=True, timeout_in_seconds=600)

        # Remove the power-management label from every host where it is present (idempotent).
        self.remove_management_label_from_all_hosts()
