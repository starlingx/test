import pytest
from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.system.healthquery.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_utils import find_target_at_least_two_ahead, find_target_beyond_skew, find_version_one_before_target, parse_minor_version
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


@mark.lab_is_simplex
def test_control_plane_upgrade_rejected_beyond_skew_policy_simplex(request: FixtureRequest) -> None:
    """Test that the 4th consecutive control-plane upgrade is rejected without kubelet upgrade.

    Starts a Kubernetes upgrade to a version 4+ minor versions ahead,
    upgrades the control-plane 3 times successfully, then verifies the
    4th control-plane upgrade is rejected by the system because the
    kubelet version skew policy (max 3 minor versions) would be violated.

    Test Steps:
        - Validate system health and find a target version 4+ minor versions ahead
        - Start upgrade, download images, pre-app-update, networking, storage, cordon
        - Upgrade control-plane 3 times successfully (one minor version each)
        - Attempt a 4th control-plane upgrade and verify it is rejected
        - Abort and delete the upgrade

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    max_control_plane_skew = 3
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)

    def teardown() -> None:
        """Cleanup kubernetes upgrade if still in progress."""
        get_logger().log_teardown_step("Abort and delete kubernetes upgrade if needed")
        try:
            kube_upgrade_keywords.kube_upgrade_abort()
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=600)
            kube_upgrade_keywords.kube_upgrade_delete()
        except Exception:
            get_logger().log_info("No kubernetes upgrade to clean up")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Check if the system is healthy for Kubernetes upgrade")
    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    get_logger().log_test_case_step("Find a target version more than 3 minor versions ahead")
    target_version = find_target_beyond_skew(active_kube_version, available_kube_versions)
    get_logger().log_info(f"Active: {active_kube_version}, Target: {target_version} " f"(gap: {parse_minor_version(target_version) - parse_minor_version(active_kube_version)} minor versions)")

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "downloaded-images",
        timeout=600,
        failure_states=["downloading-images-failed"],
    )

    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=600,
        failure_states=["pre-updating-apps-failed"],
    )

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-networking",
        timeout=600,
        failure_states=["upgrading-networking-failed"],
    )

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-storage",
        timeout=600,
        failure_states=["upgrading-storage-failed"],
    )

    get_logger().log_test_case_step("Host cordon")
    kube_upgrade_keywords.kube_host_cordon(host)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "cordon-complete",
        timeout=600,
        failure_states=["cordon-failed"],
    )

    get_logger().log_test_case_step(f"Upgrade control-plane {max_control_plane_skew} times (one minor version each)")
    for i in range(1, max_control_plane_skew + 1):
        get_logger().log_info(f"Control-plane upgrade {i}/{max_control_plane_skew}")
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(host)
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
            "upgraded-first-master",
            timeout=1200,
            failure_states=["upgrading-first-master-failed"],
        )

    get_logger().log_test_case_step("Attempt 4th control-plane upgrade and verify it is rejected")
    with pytest.raises(AssertionError):
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(host)

    get_logger().log_test_case_step("Abort the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=600)

    get_logger().log_test_case_step("Delete the aborted Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_delete()

    get_logger().log_test_case_step(f"Verify active version is still {active_kube_version}")
    current_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(current_version, active_kube_version, "Active version unchanged after aborted upgrade")


@mark.lab_has_standby_controller
def test_second_control_plane_upgrade_rejected() -> None:
    """Test that upgrading the first controller control-plane twice is rejected before upgrading the second.

    On a dual-controller lab, the control-plane must be upgraded in
    lockstep: first-master one version, then second-master to the same
    version, before the first-master can be upgraded again. This test
    verifies that attempting a second control-plane upgrade on the
    first-master (standby) is rejected when the second-master (active)
    has not yet been upgraded.

    Test Steps:
        - Validate system health and find a target version 2+ minor versions ahead
        - Start upgrade, download images, pre-app-update, networking, storage
        - Upgrade first-master control-plane once (succeeds)
        - Attempt second control-plane upgrade on first-master and verify it is rejected

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)

    get_logger().log_test_case_step("Check if the system is healthy for Kubernetes upgrade")
    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    get_logger().log_test_case_step("Find a target version at least 2 minor versions ahead")
    target_version = find_target_at_least_two_ahead(active_kube_version, available_kube_versions)
    get_logger().log_info(f"Active: {active_kube_version}, Target: {target_version}")

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "downloaded-images",
        timeout=600,
        failure_states=["downloading-images-failed"],
    )

    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "pre-updated-apps",
        timeout=600,
        failure_states=["pre-updating-apps-failed"],
    )

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-networking",
        timeout=600,
        failure_states=["upgrading-networking-failed"],
    )

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-storage",
        timeout=600,
        failure_states=["upgrading-storage-failed"],
    )

    get_logger().log_test_case_step("Upgrade first-master control-plane once")
    standby_hostname = system_host_list_keywords.get_standby_controller().get_host_name()
    get_logger().log_info(f"Upgrading control-plane on first-master: {standby_hostname}")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(standby_hostname)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
        "upgraded-first-master",
        timeout=1200,
        failure_states=["upgrading-first-master-failed"],
    )

    get_logger().log_test_case_step("Attempt second control-plane upgrade on first-master without upgrading second-master")
    with pytest.raises(AssertionError):
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(standby_hostname)


@mark.lab_has_standby_controller
def test_abort_orchestration_after_control_plane_then_manual_kubelet_and_retry() -> None:
    """Test aborting orchestrated upgrade after control-plane, manually upgrading kubelets, then retrying.

    Creates an orchestration strategy to the target version, applies it,
    then aborts after the control-plane has been upgraded to target - 1.
    Manually upgrades kubelets on all hosts to target - 1 (lock/unlock
    each host). Deletes the strategy, recreates it to the target version,
    and applies it to completion.

    Test Steps:
        - Validate system health and Kubernetes versions
        - Create orchestration strategy to target version and apply
        - Wait for control-plane to reach target - 1, then abort strategy
        - Manually upgrade kubelets on all hosts to target - 1
        - Delete the aborted strategy
        - Recreate orchestration strategy to target version and apply
        - Verify target version is active

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    kube_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)

    k8s_config = ConfigurationManager.get_k8s_config()
    target_version = k8s_config.get_k8_target_version()

    get_logger().log_test_case_step("Check if the system is healthy for Kubernetes upgrade")
    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    all_versions = available_kube_versions + [active_kube_version]
    version_before_target = find_version_one_before_target(target_version, all_versions)
    get_logger().log_info(f"Active: {active_kube_version}, Target: {target_version}, " f"Version before target: {version_before_target}")

    # === Phase 1: Orchestrated upgrade, abort after control-plane reaches target - 1 ===

    get_logger().log_test_case_step(f"Create orchestration strategy for {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply orchestration strategy")
    kube_strategy_keywords.apply_kube_upgrade_strategy_without_waiting()

    get_logger().log_test_case_step(f"Wait for first master control-plane to reach {version_before_target}")
    standby_hostname = system_host_list_keywords.get_standby_controller().get_host_name()

    kube_host_upgrade_list_keywords.wait_for_host_control_plane_version(
        standby_hostname,
        version_before_target,
        timeout=1200,
    )

    get_logger().log_test_case_step("Abort orchestration strategy")
    kube_strategy_keywords.abort_kube_upgrade_strategy()

    active_hostname = system_host_list_keywords.get_active_controller().get_host_name()
    active_cp_version = kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(active_hostname).get_control_plane_version()
    # Check if is necessary to upgrade active controller control-plane because the strategy abort
    if active_cp_version != version_before_target:
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_hostname)
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state(
            "upgraded-second-master",
            timeout=600,
            failure_states=["upgrading-second-master-failed"],
        )

    # === Phase 2: Manually upgrade kubelets on all hosts to target - 1 ===
    get_logger().log_test_case_step(f"Manually upgrade kubelets on all hosts to {version_before_target}")

    get_logger().log_test_case_step(f"Upgrade kubelet on controller {standby_hostname}")
    get_logger().log_info(f"Locking node {standby_hostname}")
    system_host_lock_keywords.lock_host(standby_hostname)
    kube_host_upgrade_keywords.kube_host_upgrade_kubelet(standby_hostname)
    kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(
        standby_hostname,
        "upgraded-kubelet",
        timeout=600,
        failure_statuses=["upgrading-kubelets-failed"],
    )
    get_logger().log_info(f"Unlock node {standby_hostname}")
    system_host_lock_keywords.unlock_host(standby_hostname)

    get_logger().log_info("Swact controllers")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_test_case_step(f"Upgrade kubelet on controller {active_hostname}")
    get_logger().log_info(f"Locking node {active_hostname}")
    system_host_lock_keywords.lock_host(active_hostname)
    kube_host_upgrade_keywords.kube_host_upgrade_kubelet(active_hostname)
    kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(
        active_hostname,
        "upgraded-kubelet",
        timeout=600,
        failure_statuses=["upgrading-kubelets-failed"],
    )
    get_logger().log_info(f"Unlock node {active_hostname}")
    system_host_lock_keywords.unlock_host(active_hostname)

    # check if lab has compute nodes to upgrade kubelet
    hosts = system_host_list_keywords.get_system_host_list().get_hosts()
    if len(hosts) > 2:
        get_logger().log_test_case_step("Upgrade kubelet on worker nodes")
        workers = system_host_list_keywords.get_system_host_list().get_computer_names()
        for worker in workers:
            get_logger().log_info(f"Locking worker node {worker}")
            system_host_lock_keywords.lock_host(worker)
            kube_host_upgrade_keywords.kube_host_upgrade_kubelet(worker)
            kube_host_upgrade_list_keywords.wait_for_host_upgrade_status(
                worker,
                "upgraded-kubelet",
                timeout=600,
                failure_statuses=["upgrading-kubelets-failed"],
            )
            get_logger().log_info(f"Unlock worker node {worker}")
            system_host_lock_keywords.unlock_host(worker)

    get_logger().log_test_case_step("Delete aborted orchestration strategy")
    kube_strategy_keywords.delete_kube_upgrade_strategy()

    # === Phase 3: Recreate strategy and complete upgrade to target ===
    get_logger().log_test_case_step("Wait for alarms to be cleared, excluding 'Kubernetes upgrade in progress' alarm")
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(["900.007"])

    get_logger().log_test_case_step(f"Recreate orchestration strategy for {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply orchestration strategy to completion")
    apply_output = kube_strategy_keywords.apply_kube_upgrade_strategy()
    validate_equals(apply_output.get_state(), "applied", "Strategy applied successfully")

    get_logger().log_test_case_step("Delete completed orchestration strategy")
    kube_strategy_keywords.delete_kube_upgrade_strategy()

    get_logger().log_test_case_step(f"Verify target version {target_version} is active")
    current_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(current_version, target_version, "Target version is now active")

    get_logger().log_test_case_step("Verify host upgraded via kube-host-upgrade-list")
    host_upgrade_list = kube_host_upgrade_list_keywords.kube_host_upgrade_list()
    controllers = system_host_list_keywords.get_system_host_list().get_controller_names()
    for controller in controllers:
        host_upgrade = host_upgrade_list.get_host_upgrade_by_hostname(controller)
        validate_equals(host_upgrade.get_control_plane_version(), target_version, f"{controller} control-plane upgraded")
        validate_equals(host_upgrade.get_kubelet_version(), target_version, f"{controller} kubelet upgraded")
    hosts = system_host_list_keywords.get_system_host_list().get_hosts()
    if len(hosts) > 2:
        workers = system_host_list_keywords.get_system_host_list().get_computer_names()
        for worker in workers:
            host_upgrade = host_upgrade_list.get_host_upgrade_by_hostname(worker)
            validate_equals(host_upgrade.get_kubelet_version(), target_version, f"{worker} kubelet upgraded")
