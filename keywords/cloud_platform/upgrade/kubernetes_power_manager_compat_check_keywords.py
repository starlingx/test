"""kubernetes-power-manager platform-upgrade compatibility keywords.

kubernetes-power-manager (KPM) is an upstream Intel application that is not part of the platform
install baseline, so the upgrade/rollback compatibility test must be able to install it first when
it is not already present. This keyword provides that install-if-missing step and the functional
check the test uses to decide whether KPM is healthy before, during, and after the platform
upgrade.

The application is updated in place by the platform during deploy activate; it is not removed
first. The functional signal this keyword actually verifies is the per-node power-node-agent
DaemonSet: a ready agent pod on every expected node (wait_for_power_node_agent_ready), which the
operator only schedules once it has reconciled the PowerConfig. The test pairs this with its own
generic namespace health check (no unhealthy pods in intel-power). The operator's
controller-manager Deployment and the power.intel.com CRDs are not asserted directly; a ready
per-node agent already implies the operator reconciled. The real CPU-knob assertions
(cpufreq/powercap) only hold on physical hardware, so they are deliberately out of scope here; this
keyword proves the app survives the upgrade/rollback, not that a given CPU C-state was applied.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class KubernetesPowerManagerCompatCheckKeywords(BaseKeyword):
    """Install-if-missing and functional checks for the KPM upgrade/rollback compatibility test.

    kubernetes-power-manager is not installed by the platform install, so unlike the other
    app-compat tests (whose application is already applied at baseline) this one has to upload and
    apply KPM first when it is absent. ensure_applied provides that idempotent step; the remaining
    keywords are the reconciliation checks the test runs at each phase.
    """

    # The per-node agent and the controller-manager are reconciled by the operator after the app
    # reports applied, so the functional check is retried rather than read once.
    RECONCILE_TIMEOUT = 300
    RECONCILE_POLL_INTERVAL = 10

    # Node label the operator's PowerConfig selects to schedule the power-node-agent DaemonSet.
    # Without it the DaemonSet is DESIRED=0 and no agent pod runs.
    POWER_MANAGEMENT_LABEL = "power-management=enabled"

    def __init__(self, ssh_connection: SSHConnection):
        """Instantiate the keyword.

        Args:
            ssh_connection(SSHConnection): active-controller SSH connection the system/kubectl
                commands run against.

        """
        self.ssh_connection = ssh_connection
        self.app_apply = SystemApplicationApplyKeywords(ssh_connection)
        self.app_list = SystemApplicationListKeywords(ssh_connection)
        self.app_remove = SystemApplicationRemoveKeywords(ssh_connection)
        self.app_upload = SystemApplicationUploadKeywords(ssh_connection)
        self.pods = KubectlGetPodsKeywords(ssh_connection)
        self.host_list = SystemHostListKeywords(ssh_connection)
        self.host_label = SystemHostLabelKeywords(ssh_connection)
        self.alarms = AlarmListKeywords(ssh_connection)

    def ensure_power_management_label(self, app_name: str) -> list[str]:
        """Assign the power-management=enabled label where missing, reapply only if it changed.

        The power-node-agent DaemonSet runs only where the node carries the label the operator's
        PowerConfig selects (power-management=enabled); without it the DaemonSet is DESIRED=0 and no
        agent pod is ever scheduled. The label is a runtime (not out-of-service) attribute, so it is
        assigned directly without a host lock, matching the manual install procedure and the
        existing power-manager setup test. Assigned on every host because on an AIO-DX the
        controllers are also the workers.

        The label is only assigned where it is not already present, so the step is idempotent:

          - On a fresh install (the label is missing) assigning it is a configuration change that
            the platform flags with 'A configuration change requires a reapply of the <app>
            application' (a persistent config-out-of-date alarm that does not self-clear). The
            application is reapplied to settle that alarm the correct way, rather than masking it as
            transient, so no config-out-of-date state reaches 'software deploy start' (which rejects
            any active alarm).
          - On a rerun against a lab that is already set up (every host already carries the label)
            nothing is assigned, no config-out-of-date alarm is raised, and the reapply plus its
            60s alarm dwell are skipped.

        Args:
            app_name(str): the platform application name to reapply when the label changed,
                e.g. "kubernetes-power-manager".

        Returns:
            list[str]: the host names this call newly labelled (empty when nothing changed), so the
                caller can remove only what it added on teardown.

        """
        key = self.POWER_MANAGEMENT_LABEL.split("=", 1)[0]
        newly_labelled: list[str] = []
        for host in self.host_list.get_system_host_list().get_hosts():
            host_name = host.get_host_name()
            current = self.host_label.get_system_host_label_list(host_name).get_label_value(key)
            if current == "enabled":
                get_logger().log_info(f"{host_name} already carries {self.POWER_MANAGEMENT_LABEL}; skipping")
                continue
            get_logger().log_info(f"assigning {self.POWER_MANAGEMENT_LABEL} to {host_name}")
            self.host_label.system_host_label_assign(host_name, self.POWER_MANAGEMENT_LABEL, overwrite=True)
            newly_labelled.append(host_name)

        if not newly_labelled:
            get_logger().log_info("power-management label already present on all hosts; no reapply needed")
            return newly_labelled

        # A label was actually assigned, which raises the config-out-of-date alarm ('requires a
        # reapply'); reapply the application to satisfy it rather than wait it out (it never
        # self-clears). Use the retrying apply: ensure_applied may have just applied the app and the
        # platform can still report an apply/reconcile in progress, which makes a bare
        # 'application-apply' get rejected ('install/update is already in progress', rc=1). The
        # retrying variant waits for that to clear, then applies and waits for 'applied'.
        get_logger().log_info(f"reapplying {app_name} to settle the label configuration change")
        self.app_apply.system_application_apply_with_retry(app_name)

        # Any remaining fallout is the transient reapply/reconcile pair (a KPM re-apply 750.004 and
        # a host config reconcile 250.001); wait for them to clear and stay clear before the caller
        # proceeds, so the later 'software deploy start' (which rejects ANY active alarm) is not
        # blocked by this step's own fallout.
        get_logger().log_info("waiting for the label-triggered reapply/reconcile alarms to clear")
        self.alarms.wait_for_all_alarms_cleared(dwell_seconds=60, transient_alarm_ids=["750.004", "250.001"])
        return newly_labelled

    def remove_power_management_label(self, host_names: list[str]) -> None:
        """Remove the power-management label from the given hosts (teardown of what the test added).

        Args:
            host_names(list[str]): the hosts to remove the label from, as returned by
                ensure_power_management_label.

        """
        key = self.POWER_MANAGEMENT_LABEL.split("=", 1)[0]
        for host_name in host_names:
            get_logger().log_info(f"removing {key} label from {host_name}")
            self.host_label.system_host_label_remove(host_name, key)

    def ensure_applied(self, app_name: str, tar_file_path: str) -> None:
        """Ensure kubernetes-power-manager is applied, installing it first if it is absent.

        This is the install-if-missing step that the other app-compat tests do not need: KPM is an
        upstream app that is not part of the install baseline, so the test cannot assume it is
        already applied. The step is idempotent so the test can run on a lab where KPM is already
        installed, already applied, or not present at all:

          - already applied  -> nothing to do.
          - present, not applied -> apply it (an interrupted or uploaded-only state).
          - absent -> upload the staged tarball, then apply it.

        Args:
            app_name(str): the platform application name, e.g. "kubernetes-power-manager".
            tar_file_path(str): path (glob allowed) to the staged KPM .tgz on the controller, used
                only when the application still has to be uploaded.

        Returns:
            bool: True if this call uploaded the application (it was absent), so the caller can
                remove only what it installed on teardown; False if it was already present.

        """
        if self.app_apply.is_already_applied(app_name):
            get_logger().log_info(f"{app_name} is already applied; no install needed")
            return False

        uploaded = False
        if not self.app_list.get_system_application_list().is_in_application_list(app_name):
            get_logger().log_info(f"{app_name} is not present; uploading from {tar_file_path}")
            upload_input = SystemApplicationUploadInput()
            upload_input.set_app_name(app_name)
            upload_input.set_tar_file_path(tar_file_path)
            self.app_upload.system_application_upload(upload_input)
            uploaded = True
        else:
            get_logger().log_info(f"{app_name} is present but not applied; applying it")

        self.app_apply.system_application_apply(app_name)
        return uploaded

    def remove_app(self, app_name: str) -> None:
        """Remove and delete an application (teardown of what this test uploaded).

        Used to return the lab to the baseline it had before the test installed the app, so a later
        test in the same lab does not inherit an app this test added. Only called for apps that
        ensure_applied reported it uploaded.

        Args:
            app_name(str): the platform application name to remove and delete.

        """
        get_logger().log_info(f"removing and deleting {app_name} (installed by this test)")
        self.app_remove.system_application_remove_and_delete_app(app_name, force_removal=True)

    def wait_for_power_node_agent_ready(self, namespace: str, expected_nodes: int) -> None:
        """Wait until the power-node-agent DaemonSet has a ready pod on every expected node.

        The per-node agent is the component that reconciles the host power state, so it is the
        signal that KPM is functional on this release rather than merely 'applied'. On a duplex lab
        the agent runs on both controllers (which are also the workers), so expected_nodes is the
        number of nodes the agent should cover.

        Args:
            namespace(str): the KPM namespace, e.g. "intel-power".
            expected_nodes(int): the number of ready power-node-agent pods expected.

        """

        def ready_agent_count() -> int:
            count = self._ready_power_node_agent_count(namespace)
            get_logger().log_info(f"power-node-agent ready pods: {count}/{expected_nodes}")
            return count

        validate_equals_with_retry(
            ready_agent_count,
            expected_nodes,
            f"power-node-agent ready on all {expected_nodes} node(s)",
            timeout=self.RECONCILE_TIMEOUT,
            polling_sleep_time=self.RECONCILE_POLL_INTERVAL,
        )

    def _ready_power_node_agent_count(self, namespace: str) -> int:
        """Return how many power-node-agent pods are Running and Ready in the namespace.

        Args:
            namespace(str): the KPM namespace.

        Returns:
            int: the number of ready power-node-agent pods.

        """
        pods = self.pods.get_pods(namespace).get_pods()
        ready = 0
        for pod in pods:
            if "power-node-agent" in pod.get_name() and pod.is_ready():
                ready += 1
        return ready
