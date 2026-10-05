"""
Validate Kubernetes upgrade orchestration failure injection scenarios.

Prerequisites
- Need to be run on lab with n-1 kubernetes version

Description:
- test_orchestrated_kube_upgrade_fails_on_control_plane_upgrade_kill_process_kubeadm - Kill kubeadm during control-plane
  upgrade to trigger orchestration apply-failed state
- test_orchestrated_kube_upgrade_fails_on_control_plane_upgrade_kill_process_sysinv - Kill sysinv-agent during
  control-plane upgrade to trigger orchestration timed-out state
- test_orchestrated_kube_upgrade_fails_on_control_plane_upgrade_stop_process - Send STOP signal to kubeadm during
  control-plane upgrade to trigger orchestration timed-out state
- test_orchestrated_kube_upgrade_fails_on_kubelet_upgrade_kill_process_sysinv - Kill sysinv-agent during kubelet upgrade
  to trigger upgrading-kubelet-failed state
- test_orchestrated_kube_upgrade_abort_on_control_plane_upgrade_kill_process_sysinv - Abort orchestration during
  control-plane upgrade while killing sysinv-agent to trigger abort timeout (Only SX lab)
- test_orchestrated_kube_upgrade_abort_on_kubelet_upgrade_kill_process_sysinv - Abort orchestration during kubelet
  upgrade while killing sysinv-agent to trigger abort timeout (Only SX lab)
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none, validate_str_contains
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_fault_injection_keywords import KubeUpgradeFaultInjectionKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.linux.pkill.pkill_keywords import PkillKeywords


def cleanup_kube_upgrade_strategy_and_entity() -> None:
    """Delete the kube-upgrade strategy and the kube-upgrade entity, then clear alarms.

    Shared teardown for the orchestrated tests. Deleting the sw-deploy/kube-upgrade
    strategy does not remove the underlying kube-upgrade entity, which can remain in a
    state such as 'upgraded-first-master' or 'upgrade-aborted' and block subsequent
    tests. This helper deletes the strategy (if present), then aborts the kube-upgrade
    only when it is not already aborted (abort returns a non-zero code once it is in
    'upgrade-aborted'), deletes the kube-upgrade entity, and waits for alarms to clear.

    A fresh SSH connection is taken so it remains valid even after a controller swact.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kube_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)

    get_logger().log_teardown_step("Delete kube-upgrade strategy if present")
    if kube_strategy_keywords.kube_upgrade_strategy_exists():
        # The abort may still be in progress (state 'aborting'); wait for the abort
        # phase to finish before deleting, since a delete during the abort can be
        # rejected. The terminal abort state varies ('aborted', 'abort-timeout', or
        # 'abort-failed'), but all reach current-phase-completion 100%, so wait on
        # that rather than a single state.
        kube_strategy_keywords.wait_for_current_phase_completion()
        kube_strategy_keywords.delete_kube_upgrade_strategy()
    else:
        get_logger().log_info("No kube-upgrade strategy to delete")

    if kube_upgrade_show_keywords.is_kube_upgrade_in_progress():
        current_state = kube_upgrade_show_keywords.kube_upgrade_show().get_kube_upgrade_show_object().get_state()
        get_logger().log_info(f"Kubernetes upgrade present in state '{current_state}'")
        # 'system kube-upgrade-abort' returns a non-zero code once the upgrade is
        # already in 'upgrade-aborted', so only abort when it is not aborted yet.
        if current_state != "upgrade-aborted":
            get_logger().log_teardown_step("Abort Kubernetes upgrade")
            kube_upgrade_keywords.kube_upgrade_abort()
            kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgrade-aborted", timeout=600)
        get_logger().log_teardown_step("Delete Kubernetes upgrade")
        kube_upgrade_keywords.kube_upgrade_delete()
    else:
        get_logger().log_info("No Kubernetes upgrade to clean up")

    get_logger().log_teardown_step("Wait for alarms to clear")
    AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared()


def test_kube_upgrade_fails_on_control_plane_upgrade_kill_process_kubeadm(request: FixtureRequest) -> None:
    """Test that killing a process during control-plane upgrade fails orchestration.

    Creates and applies a Kubernetes upgrade orchestration strategy, waits
    for the upgrade to reach the control-plane upgrade phase
    (kube-host-upgrade-control-plane), then repeatedly kills the target
    process until the orchestration strategy reaches apply-failed state.

    Test Steps:
        - Validate system health and Kubernetes versions
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the control-plane upgrade phase
        - Kill the target process in a loop until strategy state is apply-failed
        - Verify the orchestration strategy is in apply-failed state
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    process_to_kill = "[k]ubeadm"

    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    request.addfinalizer(cleanup_kube_upgrade_strategy_and_entity)

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")

    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy (non-blocking)")
    kube_strategy_keywords.apply_kube_upgrade_strategy_without_waiting()

    get_logger().log_test_case_step("Wait for strategy to reach control-plane upgrade phase")
    kube_strategy_keywords.wait_for_kube_upgrade_step("kube-host-upgrade-control-plane", timeout=600)

    get_logger().log_test_case_step(f"Kill '{process_to_kill}' in loop until strategy reaches apply-failed")
    KubeUpgradeFaultInjectionKeywords(ssh_connection).kill_process_until_state(process_to_kill, kube_strategy_keywords.get_apply_result, ["failed"], timeout=600)

    get_logger().log_test_case_step("Verify apply-reason contains upgrading-first-master-failed")
    strategy_obj = kube_strategy_keywords.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()
    apply_reason = strategy_obj.get_apply_reason()
    validate_str_contains(apply_reason, "upgrading-first-master-failed", "Apply reason indicates first master upgrade failure")


def test_kube_upgrade_fails_on_control_plane_upgrade_kill_process_sysinv(request: FixtureRequest) -> None:
    """Test that killing sysinv-agent during control-plane upgrade causes orchestration to time out.

    Creates and applies a Kubernetes upgrade orchestration strategy, waits
    for the upgrade to reach the control-plane upgrade phase
    (kube-host-upgrade-control-plane), then repeatedly kills sysinv-agent
    until the orchestration strategy reaches timed-out state.

    Test Steps:
        - Validate system health and Kubernetes versions
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the control-plane upgrade phase
        - Kill sysinv-agent in a loop until strategy state is timed-out
        - Wait for current-phase-completion to reach 100%
        - Verify apply-reason contains 'kube-host-upgrade-control-plane timed out'
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    process_to_kill = "sysinv-agent"

    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    request.addfinalizer(cleanup_kube_upgrade_strategy_and_entity)

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")

    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy (non-blocking)")
    kube_strategy_keywords.apply_kube_upgrade_strategy_without_waiting()

    get_logger().log_test_case_step("Wait for strategy to reach control-plane upgrade phase")
    kube_strategy_keywords.wait_for_kube_upgrade_step("kube-host-upgrade-control-plane", timeout=600)

    get_logger().log_test_case_step(f"Kill '{process_to_kill}' in loop until strategy reaches apply-failed")
    KubeUpgradeFaultInjectionKeywords(ssh_connection).kill_process_until_state(process_to_kill, kube_strategy_keywords.get_apply_result, ["timed-out"], timeout=600)

    get_logger().log_test_case_step("Wait for current-phase-completion to reach 100%")
    kube_strategy_keywords.wait_for_current_phase_completion()

    get_logger().log_test_case_step("Verify apply-reason contains kube-host-upgrade-control-plane timed out")
    strategy_obj = kube_strategy_keywords.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()
    apply_reason = strategy_obj.get_apply_reason()
    validate_str_contains(apply_reason, "kube-host-upgrade-control-plane timed out", "Apply reason indicates first master upgrade failure")


def test_kube_upgrade_fails_on_control_plane_upgrade_stop_process(request: FixtureRequest) -> None:
    """Test that sending STOP signal to kubeadm during control-plane upgrade causes orchestration to time out.

    Creates and applies a Kubernetes upgrade orchestration strategy, waits
    for the upgrade to reach the control-plane upgrade phase
    (kube-host-upgrade-control-plane), then repeatedly sends STOP signal to
    the target process until the orchestration strategy reaches timed-out state.

    Test Steps:
        - Validate system health and Kubernetes versions
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the control-plane upgrade phase
        - Send STOP signal to kubeadm in a loop until strategy state is timed-out
        - Wait for current-phase-completion to reach 100%
        - Verify apply-reason contains 'kube-host-upgrade-control-plane timed out'
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    process_to_kill = "[k]ubeadm"

    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    request.addfinalizer(cleanup_kube_upgrade_strategy_and_entity)

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")

    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy (non-blocking)")
    kube_strategy_keywords.apply_kube_upgrade_strategy_without_waiting()

    get_logger().log_test_case_step("Wait for strategy to reach control-plane upgrade phase")
    kube_strategy_keywords.wait_for_kube_upgrade_step("kube-host-upgrade-control-plane", timeout=600)

    get_logger().log_test_case_step(f"Send STOP signal to '{process_to_kill}' in loop until strategy reaches apply-failed")
    KubeUpgradeFaultInjectionKeywords(ssh_connection).stop_process_until_state(process_to_kill, kube_strategy_keywords.get_apply_result, ["timed-out"], timeout=600)

    get_logger().log_test_case_step("Wait for current-phase-completion to reach 100%")
    kube_strategy_keywords.wait_for_current_phase_completion()

    get_logger().log_test_case_step("Verify apply-reason contains kube-host-upgrade-control-plane timed out")
    strategy_obj = kube_strategy_keywords.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()
    apply_reason = strategy_obj.get_apply_reason()
    validate_str_contains(apply_reason, "kube-host-upgrade-control-plane timed out", "Apply reason indicates first master upgrade failure")


def test_kube_upgrade_fails_on_kubelet_upgrade_kill_process_sysinv(request: FixtureRequest) -> None:
    """Test that killing sysinv-agent during kubelet upgrade causes the kubelet upgrade to fail.

    Starts a manual Kubernetes upgrade, upgrades control-plane on all controllers,
    then initiates the kubelet upgrade and repeatedly kills sysinv-agent until
    the host upgrade status reaches 'upgrading-kubelet-failed' as reported by
    'system kube-host-upgrade-list'.

    Test Steps:
        - Validate system health and Kubernetes versions
        - Download images, run pre-app-update, upgrade networking and storage
        - Upgrade control-plane on all controllers
        - Initiate kubelet upgrade on target host
        - Kill sysinv-agent in a loop until kube-host-upgrade-list shows 'upgrading-kubelet-failed' for target host
        - Verify the kubelet upgrade status is 'upgrading-kubelet-failed'
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    process_to_kill = "sysinv-agent"

    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    pkill_keywords = PkillKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()
    is_simplex = ConfigurationManager.get_lab_config().get_lab_type() == "Simplex"

    request.addfinalizer(cleanup_kube_upgrade_strategy_and_entity)

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")

    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("downloaded-images", timeout=600, failure_states=["downloading-images-failed"])

    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("pre-updated-apps", timeout=600, failure_states=["pre-updating-apps-failed"])

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-networking", timeout=600, failure_states=["upgrading-networking-failed"])

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-storage", timeout=600, failure_states=["upgrading-storage-failed"])

    active_hostname = system_host_list_keywords.get_active_controller().get_host_name()
    if is_simplex:
        get_logger().log_test_case_step(f"Upgrade control-plane on {active_hostname}")
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_hostname)
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-first-master", timeout=600, failure_states=["upgrading-first-master-failed"])

        target_hostname = active_hostname
    else:
        standby_hostname = system_host_list_keywords.get_standby_controller().get_host_name()

        get_logger().log_test_case_step(f"Upgrade control-plane on standby {standby_hostname}")
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(standby_hostname)
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-first-master", timeout=600, failure_states=["upgrading-first-master-failed"])

        get_logger().log_test_case_step(f"Upgrade control-plane on active {active_hostname}")
        kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_hostname)
        kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-second-master", timeout=600, failure_states=["upgrading-second-master-failed"])

        get_logger().log_test_case_step(f"Lock standby controller {standby_hostname}")
        system_host_lock_keywords.lock_host(standby_hostname)

        target_hostname = standby_hostname

    get_logger().log_test_case_step(f"Initiate kubelet upgrade on {target_hostname}")
    pkill_keywords.pkill_by_pattern(process_to_kill, send_as_sudo=True)
    kube_host_upgrade_keywords.kube_host_upgrade_kubelet(target_hostname)

    get_logger().log_test_case_step(f"Kill '{process_to_kill}' in loop until kubelet upgrade fails on {target_hostname}")
    KubeUpgradeFaultInjectionKeywords(ssh_connection).kill_process_until_host_upgrade_status(process_to_kill, target_hostname, "upgrading-kubelet-failed", timeout=900)


def test_kube_upgrade_abort_on_control_plane_upgrade_kill_process_sysinv(request: FixtureRequest) -> None:
    """Test that aborting during control-plane upgrade while killing sysinv-agent results in abort timeout.

    Creates and applies a Kubernetes upgrade orchestration strategy, waits
    for the upgrade to reach the control-plane upgrade phase
    (kube-host-upgrade-control-plane), then aborts the strategy and
    repeatedly kills sysinv-agent until the orchestration strategy reaches
    aborted state.

    Test Steps:
        - Validate system health and Kubernetes versions
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the control-plane upgrade phase
        - Abort the Kubernetes upgrade strategy
        - Kill sysinv-agent in a loop until strategy state is aborted
        - Wait for current-phase-completion to reach 100%
        - Verify abort-reason contains 'kube-upgrade-abort timed out'
        - Cleanup: abort upgrade, delete strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    process_to_kill = "sysinv-agent"

    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    request.addfinalizer(cleanup_kube_upgrade_strategy_and_entity)

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")

    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy (non-blocking)")
    kube_strategy_keywords.apply_kube_upgrade_strategy_without_waiting()

    get_logger().log_test_case_step("Wait for strategy to reach control-plane upgrade phase")
    kube_strategy_keywords.wait_for_kube_upgrade_step("kube-host-upgrade-control-plane", timeout=600)

    get_logger().log_test_case_step("Abort the Kubernetes upgrade strategy")
    kube_strategy_keywords.abort_kube_upgrade_strategy_without_waiting()

    get_logger().log_test_case_step(f"Kill '{process_to_kill}' in loop until strategy reaches apply-failed")
    KubeUpgradeFaultInjectionKeywords(ssh_connection).kill_process_until_state(process_to_kill, kube_strategy_keywords.get_apply_result, ["aborted"], timeout=600)

    get_logger().log_test_case_step("Wait for current-phase-completion to reach 100%")
    kube_strategy_keywords.wait_for_current_phase_completion()

    get_logger().log_test_case_step("Verify apply-reason contains kube-host-upgrade-control-plane timed out")
    strategy_obj = kube_strategy_keywords.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()
    abort_reason = strategy_obj.get_abort_reason()
    validate_str_contains(abort_reason, "kube-upgrade-abort timed out", "Apply reason indicates first master upgrade failure")


@mark.lab_is_simplex
def test_kube_upgrade_abort_on_kubelet_upgrade_kill_process_sysinv(request: FixtureRequest) -> None:
    """Test that aborting a manual upgrade during kubelet phase while killing sysinv-agent causes kubelet upgrade failure.

    Performs a manual Kubernetes upgrade (start, download images, networking,
    storage, control-plane), then initiates kubelet upgrade on the active
    controller, aborts the upgrade, and repeatedly kills sysinv-agent until
    the host upgrade status reaches 'upgrading-kubelet-failed'.

    Note:
        This test is restricted to simplex labs because on non-simplex
        systems the kubelet upgrade step completes faster than the
        orchestration status polling interval, causing the abort to
        consistently occur after the kubelet upgrade has already finished
        rather than during it, making the fault injection ineffective.

    Test Steps:
        - Validate system health and Kubernetes versions
        - Start manual Kubernetes upgrade to target version
        - Download images, run pre-app-update, upgrade networking and storage
        - Upgrade control-plane on active controller
        - Initiate kubelet upgrade on active controller
        - Abort the Kubernetes upgrade
        - Kill sysinv-agent in a loop until kube-host-upgrade-list shows 'upgrading-kubelet-failed'
        - Verify the kubelet upgrade status is 'upgrading-kubelet-failed'
        - Cleanup: abort upgrade

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    process_to_kill = "sysinv-agent"

    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    kube_upgrade_keywords = KubeUpgradeKeywords(ssh_connection)
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_keywords = KubeHostUpgradeKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    request.addfinalizer(cleanup_kube_upgrade_strategy_and_entity)

    get_logger().log_test_case_step("Validate active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found: {active_kube_version}")
    available_kube_versions = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_versions, f"Available Kubernetes versions found: {available_kube_versions}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_versions)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")

    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Start Kubernetes upgrade to {target_version}")
    start_output = kube_upgrade_keywords.kube_upgrade_start(target_version)
    validate_equals(start_output.get_kube_upgrade_show_object().get_state(), "upgrade-started", "Upgrade started")

    get_logger().log_test_case_step("Download Kubernetes images")
    kube_upgrade_keywords.kube_upgrade_download_images()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("downloaded-images", timeout=600, failure_states=["downloading-images-failed"])

    get_logger().log_test_case_step("Run pre-application-update")
    kube_upgrade_keywords.kube_pre_application_update()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("pre-updated-apps", timeout=600, failure_states=["pre-updating-apps-failed"])

    get_logger().log_test_case_step("Upgrade networking")
    kube_upgrade_keywords.kube_upgrade_networking()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-networking", timeout=600, failure_states=["upgrading-networking-failed"])

    get_logger().log_test_case_step("Upgrade storage")
    kube_upgrade_keywords.kube_upgrade_storage()
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-storage", timeout=600, failure_states=["upgrading-storage-failed"])

    active_hostname = system_host_list_keywords.get_active_controller().get_host_name()
    get_logger().log_test_case_step(f"Upgrade control-plane on {active_hostname}")
    kube_host_upgrade_keywords.kube_host_upgrade_control_plane(active_hostname)
    kube_upgrade_show_keywords.wait_for_kube_upgrade_state("upgraded-first-master", timeout=600, failure_states=["upgrading-first-master-failed"])

    target_hostname = active_hostname

    get_logger().log_test_case_step(f"Initiate kubelet upgrade on {target_hostname}")
    kube_host_upgrade_keywords.kube_host_upgrade_kubelet(target_hostname)

    get_logger().log_test_case_step("Abort the Kubernetes upgrade")
    kube_upgrade_keywords.kube_upgrade_abort()

    get_logger().log_test_case_step(f"Kill '{process_to_kill}' in loop until kubelet upgrade fails on {target_hostname}")
    KubeUpgradeFaultInjectionKeywords(ssh_connection).kill_process_until_host_upgrade_status(process_to_kill, target_hostname, "upgrading-kubelet-failed", timeout=600)
