from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than, validate_list_contains, validate_not_none
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.system.health_query.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_utils import resolve_next_hop_candidates
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager

# Config-reapply alarms raised transiently after a Kubernetes hop (cert-manager /
# oidc-auth-apps reconcile). They are NOT management affecting but still block
# sw-manager kube-upgrade-strategy build, so the settle wait must let them clear.
CONFIG_REAPPLY_BLOCKING_ALARM_IDS = ["750.004", "750.006"]


@mark.p2
@mark.lab_has_standby_controller
def test_legacy_multi_hop_k8s_upgrade(request: FixtureRequest) -> None:
    """Test legacy multi-hop Kubernetes upgrade orchestration (one strategy per version).

    Legacy (pre-USM) Kubernetes upgrade cannot jump multiple minor versions in a single
    sw-manager kube-upgrade-strategy: only the immediate next version is 'available' at a
    time. This test walks the version chain one hop at a time (for example
    v1.18.1 -> v1.19.13 -> v1.20.9 -> v1.21.8), creating, applying, and deleting a
    separate orchestration strategy for each hop until the final target configured in
    kubernetes_upgrade_config is active.

    The strategy apply tolerates the controller swact / host lock-unlock-reboot that each
    hop performs: SwManagerKubeUpgradeStrategyKeywords.apply_kube_upgrade_strategy polls
    the strategy state, retries while the sw-manager API / SSH session is transiently
    unavailable, and fails fast on a terminal Apply-failed / Aborted state.

    Test Steps:
        - Set up SSH connection to the active controller.
        - Resolve the final target Kubernetes version from configuration.
        - For each hop until the active version equals the final target:
            - Confirm the system is healthy for a Kubernetes upgrade.
            - Resolve the next available version toward the target.
            - Create the kube-upgrade-strategy for that version.
            - Apply the strategy and wait for completion (survives swact).
            - Verify the hop's target version is now active.
            - Delete the strategy before the next hop.
        - Verify the final target version is active.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    get_logger().log_info("Establishing SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()
    get_logger().log_info("Kubernetes upgrade configuration loaded successfully")

    kube_upgrade_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    health_query_keywords = SystemHealthQueryKeywords(ssh_connection)
    alarm_list_keywords = AlarmListKeywords(ssh_connection)

    def cleanup_strategy() -> None:
        """Ensure any lingering kube-upgrade-strategy is deleted after the test."""
        get_logger().log_teardown_step("Delete orchestration strategy")
        kube_upgrade_keywords.delete_kube_upgrade_strategy()

    request.addfinalizer(cleanup_strategy)

    # Resolve the final target version for the whole chain from configuration.
    final_target = kubernetes_upgrade_config.get_k8_target_version()
    validate_not_none(final_target, "Final target Kubernetes version is configured")
    validate_equals(final_target != "None", True, "Final target Kubernetes version is set (not 'None')")
    get_logger().log_info(f"Final target Kubernetes version for the chain: {final_target}")

    # Confirm the configured target is a known version on this system before starting.
    all_versions = system_kube_keywords.get_all_kubernetes_versions()
    validate_list_contains(final_target, all_versions, "Final target version exists in kube-version-list")

    active_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    get_logger().log_info(f"Starting active Kubernetes version: {active_version}")

    hop_number = 0
    while active_version != final_target:
        hop_number += 1

        get_logger().log_test_case_step(f"Hop {hop_number}: wait for blocking alarms to clear before creating the strategy")
        alarm_list_keywords.wait_for_mgmt_affecting_alarms_cleared(additional_blocking_alarm_ids=CONFIG_REAPPLY_BLOCKING_ALARM_IDS)

        get_logger().log_test_case_step(f"Hop {hop_number}: confirm system is healthy for Kubernetes upgrade")
        health_output = health_query_keywords.get_kube_upgrade_health_status()
        failed_checks = health_output.get_failed_checks()
        blocking_failures = health_query_keywords.count_blocking_health_failures(failed_checks)
        validate_equals(blocking_failures, 0, "No blocking health-query-kube-upgrade failures (management-affecting alarms or other failed checks)")

        get_logger().log_test_case_step(f"Hop {hop_number}: resolve next Kubernetes version toward {final_target}")
        available_versions = system_kube_keywords.get_kubernetes_versions_by_state("available")
        get_logger().log_info(f"Available Kubernetes versions for this hop: {available_versions}")
        next_hop_candidates = resolve_next_hop_candidates(active_version, available_versions, final_target)
        validate_greater_than(len(next_hop_candidates), 0, f"An available Kubernetes version exists between active {active_version} and target {final_target}")
        next_version = next_hop_candidates[0]
        validate_list_contains(next_version, available_versions, "Next hop version is in the available list")
        get_logger().log_info(f"Hop {hop_number}: upgrading from {active_version} to {next_version}")

        get_logger().log_test_case_step(f"Hop {hop_number}: create Kubernetes upgrade strategy for {next_version}")
        create_output = kube_upgrade_keywords.create_sw_manager_kube_upgrade_strategy(
            target_kube_version=next_version,
            controller_apply_type=kubernetes_upgrade_config.get_controller_apply_type(),
            storage_apply_type=kubernetes_upgrade_config.get_storage_apply_type(),
            worker_apply_type=kubernetes_upgrade_config.get_worker_apply_type(),
            instance_action=kubernetes_upgrade_config.get_instance_action(),
            alarm_restrictions=kubernetes_upgrade_config.get_alarm_restrictions(),
            max_parallel_worker_hosts=kubernetes_upgrade_config.get_max_parallel_worker_hosts(),
        )
        validate_equals(create_output.get_state(), "ready-to-apply", f"Hop {hop_number}: strategy is ready to apply")

        get_logger().log_test_case_step(f"Hop {hop_number}: apply Kubernetes upgrade strategy for {next_version}")
        apply_output = kube_upgrade_keywords.apply_kube_upgrade_strategy()
        validate_equals(apply_output.get_state(), "applied", f"Hop {hop_number}: strategy is applied")

        get_logger().log_test_case_step(f"Hop {hop_number}: verify {next_version} is the active version")
        active_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
        validate_equals(active_version, next_version, f"Hop {hop_number}: target version {next_version} is active")

        get_logger().log_test_case_step(f"Hop {hop_number}: delete the applied Kubernetes upgrade strategy")
        kube_upgrade_keywords.delete_kube_upgrade_strategy()

    get_logger().log_test_case_step(f"Verify final target version {final_target} is active after {hop_number} hop(s)")
    active_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(active_version, final_target, "Final target Kubernetes version is active on all hosts")
    get_logger().log_info(f"Legacy multi-hop Kubernetes upgrade to {final_target} completed in {hop_number} hop(s)")
