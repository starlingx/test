from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than
from keywords.cloud_platform.dcmanager.dcmanager_kube_deploy_strategy_keywords import DcmanagerKubeStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from pytest import mark

# Config-reapply alarms raised transiently after a Kubernetes hop (cert-manager /
# oidc-auth-apps reconcile). They are NOT management affecting but still block
# dcmanager/sw-manager strategy build, so the settle wait must let them clear.
CONFIG_REAPPLY_BLOCKING_ALARM_IDS = ["750.004", "750.006"]

# Upgrade all subclouds together; at least 10 in parallel as required.
SUBCLOUD_APPLY_TYPE = "parallel"
MAX_PARALLEL_SUBCLOUDS = 10


@mark.p2
@mark.lab_has_subcloud
def test_dc_subcloud_parallel_kube_upgrade(request) -> None:
    """Upgrade Kubernetes on all subclouds in parallel, one version hop at a time.

    Distributed Cloud Kubernetes orchestration upgrades every managed online subcloud
    toward the System Controller's active Kubernetes version. Legacy orchestration only
    advances one minor version per strategy (the next 'available' version), so this walks
    the chain one hop at a time, creating a parallel strategy (all subclouds together) per
    hop until the subclouds are in-sync with the central's active version.

    Each hop waits for blocking alarms to clear first: the management-affecting alarms, plus
    the transient 750.004 / 750.006 config-reapply alarms that are not management affecting
    yet still block strategy build after a hop. Subcloud sync status is read from the central
    (dcmanager subcloud list) rather than by logging into subclouds during the upgrade.

    Test Steps:
        - Connect to the active System Controller.
        - Read the central's active Kubernetes version (the target for the subclouds).
        - Confirm there is at least one managed subcloud and all are currently out-of-sync.
        - Loop until all subclouds report kubernetes sync in-sync:
            - Wait for management-affecting and config-reapply alarms to clear.
            - Create a parallel kube-upgrade strategy (all subclouds) toward the target.
            - Apply the strategy and wait for completion.
            - Delete the strategy.
        - Verify every subcloud is in-sync with the central's active Kubernetes version.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    kube_strategy_keywords = DcmanagerKubeStrategyKeywords(central_ssh)
    subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    system_kube_keywords = SystemKubernetesListKeywords(central_ssh)
    alarm_list_keywords = AlarmListKeywords(central_ssh)

    def cleanup_strategy() -> None:
        """Delete any lingering kube-upgrade strategy after the test."""
        get_logger().log_teardown_step("Delete DC kube-upgrade strategy if present")
        try:
            kube_strategy_keywords.dcmanager_kube_strategy_delete()
        except Exception:
            get_logger().log_info("No DC kube-upgrade strategy to delete")

    request.addfinalizer(cleanup_strategy)

    get_logger().log_test_case_step("Read the central active Kubernetes version (subcloud target)")
    central_active_version = system_kube_keywords.get_kubernetes_versions_by_state("active")[0]
    get_logger().log_info(f"Central active Kubernetes version (target for subclouds): {central_active_version}")

    get_logger().log_test_case_step("Confirm there are managed subclouds to upgrade")
    subclouds = subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects()
    subcloud_names = [subcloud.get_name() for subcloud in subclouds]
    validate_greater_than(len(subcloud_names), 0, "At least one subcloud is present for Kubernetes upgrade")
    get_logger().log_info(f"Subclouds to upgrade in parallel: {subcloud_names}")

    def all_subclouds_kube_in_sync() -> bool:
        """Check that every subcloud reports kubernetes sync status in-sync.

        Returns:
            bool: True when all subclouds are in-sync for Kubernetes, False otherwise.
        """
        current_subclouds = subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects()
        for subcloud in current_subclouds:
            if subcloud.get_sync() != "in-sync":
                return False
        return True

    hop_number = 0
    while not all_subclouds_kube_in_sync():
        hop_number += 1

        get_logger().log_test_case_step(f"Hop {hop_number}: wait for blocking alarms to clear before creating the strategy")
        alarm_list_keywords.wait_for_mgmt_affecting_alarms_cleared(additional_blocking_alarm_ids=CONFIG_REAPPLY_BLOCKING_ALARM_IDS)

        get_logger().log_test_case_step(f"Hop {hop_number}: create parallel DC kube-upgrade strategy toward {central_active_version}")
        kube_strategy_keywords.dcmanager_kube_upgrade_strategy_create(
            kube_version=central_active_version,
            subcloud_apply_type=SUBCLOUD_APPLY_TYPE,
            max_parallel_subclouds=MAX_PARALLEL_SUBCLOUDS,
        )
        # Re-read a fresh 'show' for the assertion: the create/apply return objects are
        # captured at command time, so their state can be stale even though the keyword's
        # internal wait already reached the target state.
        created_state = kube_strategy_keywords.get_dcmanager_kube_strategy_step_show().get_dcmanager_kube_strategy_step_show().get_state()
        validate_equals(created_state, "initial", f"Hop {hop_number}: strategy created in initial state")

        get_logger().log_test_case_step(f"Hop {hop_number}: apply the DC kube-upgrade strategy and wait for completion")
        # dcmanager_kube_upgrade_strategy_apply() internally waits until the strategy state
        # reaches 'complete' (or raises on timeout), so a fresh 'show' here must read 'complete'.
        kube_strategy_keywords.dcmanager_kube_upgrade_strategy_apply()
        applied_state = kube_strategy_keywords.get_dcmanager_kube_strategy_step_show().get_dcmanager_kube_strategy_step_show().get_state()
        validate_equals(applied_state, "complete", f"Hop {hop_number}: strategy applied to completion")

        get_logger().log_test_case_step(f"Hop {hop_number}: delete the applied DC kube-upgrade strategy")
        kube_strategy_keywords.dcmanager_kube_strategy_delete()

    get_logger().log_test_case_step(f"Verify all subclouds are in-sync with central version {central_active_version} after {hop_number} hop(s)")
    validate_equals(all_subclouds_kube_in_sync(), True, "All subclouds are in-sync for Kubernetes after upgrade")
    get_logger().log_info(f"All subclouds upgraded to central Kubernetes version {central_active_version} in {hop_number} hop(s)")
