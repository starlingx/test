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

import time

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_keywords import KubeHostUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_keywords import KubeUpgradeKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.linux.pkill.pkill_keywords import PkillKeywords


def _kill_process_until_apply_result(pkill_keywords: PkillKeywords, kube_strategy_keywords: SwManagerKubeUpgradeStrategyKeywords, process_pattern: str, apply_result: str, timeout: int = 600) -> bool:
    """Kill a process in a loop until the orchestration strategy state reaches the expected apply result.

    Continuously kills the specified process (via pkill) and polls the
    sw-manager kube-upgrade-strategy show command to check whether the
    orchestration apply-result has transitioned to the expected failure
    state. This simulates a fault injection scenario where a critical
    process is repeatedly terminated during an active Kubernetes upgrade
    orchestration, forcing the strategy into an error state (e.g.,
    'failed', 'timed-out', or 'aborted').

    The loop tolerates transient failures from both the pkill command
    (process may not exist between respawns) and the sw-manager query
    (system may be temporarily unresponsive during the disruption).

    Args:
        pkill_keywords (PkillKeywords): Keywords for killing processes.
        kube_strategy_keywords (SwManagerKubeUpgradeStrategyKeywords): Keywords for sw-manager kube-upgrade-strategy commands.
        process_pattern (str): Process pattern to kill (e.g., '[k]ubeadm', 'sysinv-agent').
        apply_result (str): Expected apply result state (e.g., 'failed', 'timed-out', 'aborted').
        timeout (int): Maximum wait time in seconds. Defaults to 1800 (30 minutes).

    Returns:
        bool: True if the expected apply result state was reached within the timeout, False otherwise.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            get_logger().log_info(f"Killing process matching '{process_pattern}'")
            pkill_keywords.pkill_by_pattern(process_pattern, send_as_sudo=True)
        except Exception as e:
            get_logger().log_info(f"Failed to kill '{process_pattern}': {e}, retrying")
        try:
            strategy_output = kube_strategy_keywords.show_kube_upgrade_strategy()
            state = strategy_output.get_swmanager_kube_upgrade_strategy_show().get_apply_result()
            get_logger().log_info(f"Current strategy state: {state}")
            if state == apply_result:
                return True
        except Exception:
            get_logger().log_info("sw-manager command failed during polling, retrying")
    return False


def _stop_process_until_apply_result(pkill_keywords: PkillKeywords, kube_strategy_keywords: SwManagerKubeUpgradeStrategyKeywords, process_name: str, apply_result: str, timeout: int = 600) -> bool:
    """Send STOP signal to a process in a loop until the orchestration strategy state reaches the expected apply result.

    Args:
        pkill_keywords (PkillKeywords): Keywords for killing processes.
        kube_strategy_keywords (SwManagerKubeUpgradeStrategyKeywords): Keywords for sw-manager kube-upgrade-strategy commands.
        process_name (str): Process name to send STOP signal to.
        apply_result (str): Expected apply result state (e.g., 'timed-out').
        timeout (int): Maximum wait time in seconds.

    Returns:
        bool: True if the expected apply result state was reached.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            get_logger().log_info(f"Sending STOP signal to '{process_name}'")
            pkill_keywords.pkill_signal("STOP", process_name)
        except Exception as e:
            get_logger().log_info(f"Failed to send STOP to '{process_name}': {e}, retrying")
        try:
            strategy_output = kube_strategy_keywords.show_kube_upgrade_strategy()
            state = strategy_output.get_swmanager_kube_upgrade_strategy_show().get_apply_result()
            get_logger().log_info(f"Current strategy state: {state}")
            if state == apply_result:
                return True
        except Exception:
            get_logger().log_info("sw-manager command failed during polling, retrying")
    return False


def _kill_process_until_host_upgrade_status(pkill_keywords: PkillKeywords, kube_host_upgrade_list_keywords: KubeHostUpgradeListKeywords, process_pattern: str, hostname: str, expected_status: str, timeout: int = 600) -> bool:
    """Kill a process in a loop until the host upgrade status reaches the expected value.

    Continuously kills the specified process (via pkill) and polls the
    'system kube-host-upgrade-list' command to check whether the per-host
    upgrade status has transitioned to the expected failure state. This is
    used for fault injection during the kubelet upgrade phase of a manual
    Kubernetes upgrade, where killing a process like sysinv-agent prevents
    the kubelet upgrade from completing successfully, resulting in a
    'upgrading-kubelet-failed' status for the target host.

    Unlike _kill_process_until_apply_result which monitors the orchestration
    strategy's overall apply-result, this function monitors the per-host
    upgrade status reported by 'system kube-host-upgrade-list', making it
    suitable for manual (non-orchestrated) upgrade scenarios.

    The loop tolerates transient failures from both the pkill command
    and the kube-host-upgrade-list query.

    Args:
        pkill_keywords (PkillKeywords): Keywords for killing processes.
        kube_host_upgrade_list_keywords (KubeHostUpgradeListKeywords): Keywords for system kube-host-upgrade-list.
        process_pattern (str): Process pattern to kill (e.g., 'sysinv-agent').
        hostname (str): Target hostname to check status for.
        expected_status (str): Expected status value (e.g., 'upgrading-kubelet-failed').
        timeout (int): Maximum wait time in seconds. Defaults to 1800 (30 minutes).

    Returns:
        bool: True if the expected status was reached within the timeout, False otherwise.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            get_logger().log_info(f"Killing process matching '{process_pattern}'")
            pkill_keywords.pkill_by_pattern(process_pattern, send_as_sudo=True)
        except Exception as e:
            get_logger().log_info(f"Failed to kill '{process_pattern}': {e}, retrying")
        try:
            host_upgrade = kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(hostname)
            status = host_upgrade.get_status()
            get_logger().log_info(f"Current host upgrade status for '{hostname}': {status}")
            if status == expected_status:
                return True
        except Exception:
            get_logger().log_info("kube-host-upgrade-list command failed during polling, retrying")
    return False


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
    pkill_keywords = PkillKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    def teardown() -> None:
        """Cleanup orchestration strategy and kubernetes upgrade."""
        get_logger().log_teardown_step("Cleanup orchestration strategy and kubernetes upgrade")
        try:
            kube_strategy_keywords.abort_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to abort")
        try:
            kube_strategy_keywords.wait_for_aborted()
            kube_strategy_keywords.delete_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to delete")

    request.addfinalizer(teardown)

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
    apply_failed = _kill_process_until_apply_result(pkill_keywords, kube_strategy_keywords, process_to_kill, "failed", timeout=600)
    validate_equals(apply_failed, True, f"Orchestration strategy reached apply-failed after killing '{process_to_kill}'")

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
    pkill_keywords = PkillKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    def teardown() -> None:
        """Cleanup orchestration strategy and kubernetes upgrade."""
        get_logger().log_teardown_step("Cleanup orchestration strategy and kubernetes upgrade")
        try:
            kube_strategy_keywords.abort_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to abort")
        try:
            kube_strategy_keywords.wait_for_aborted()
            kube_strategy_keywords.delete_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to delete")

    request.addfinalizer(teardown)

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
    apply_failed = _kill_process_until_apply_result(pkill_keywords, kube_strategy_keywords, process_to_kill, "timed-out", timeout=600)
    validate_equals(apply_failed, True, f"Orchestration strategy reached apply-failed after killing '{process_to_kill}'")

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
    pkill_keywords = PkillKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    def teardown() -> None:
        """Cleanup orchestration strategy and kubernetes upgrade."""
        get_logger().log_teardown_step("Cleanup orchestration strategy and kubernetes upgrade")
        try:
            kube_strategy_keywords.abort_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to abort")
        try:
            kube_strategy_keywords.wait_for_aborted()
            kube_strategy_keywords.delete_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to delete")

    request.addfinalizer(teardown)

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
    apply_failed = _stop_process_until_apply_result(pkill_keywords, kube_strategy_keywords, process_to_kill, "timed-out", timeout=600)
    validate_equals(apply_failed, True, f"Orchestration strategy reached apply-failed after killing '{process_to_kill}'")

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

    def teardown() -> None:
        """Cleanup kubernetes upgrade."""
        get_logger().log_teardown_step("Cleanup kubernetes upgrade")
        try:
            kube_upgrade_keywords.kube_upgrade_abort()
        except Exception:
            get_logger().log_info("No upgrade to abort")

    request.addfinalizer(teardown)

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
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    kubelet_failed = _kill_process_until_host_upgrade_status(pkill_keywords, kube_host_upgrade_list_keywords, process_to_kill, target_hostname, "upgrading-kubelet-failed", timeout=600)
    validate_equals(kubelet_failed, True, f"Kubelet upgrade on '{target_hostname}' reached upgrading-kubelet-failed after killing '{process_to_kill}'")


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
    pkill_keywords = PkillKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    def teardown() -> None:
        """Cleanup orchestration strategy and kubernetes upgrade."""
        get_logger().log_teardown_step("Cleanup orchestration strategy and kubernetes upgrade")
        try:
            kube_strategy_keywords.abort_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to abort")
        try:
            kube_strategy_keywords.wait_for_aborted()
            kube_strategy_keywords.delete_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to delete")

    request.addfinalizer(teardown)

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
    apply_failed = _kill_process_until_apply_result(pkill_keywords, kube_strategy_keywords, process_to_kill, "aborted", timeout=600)
    validate_equals(apply_failed, True, f"Orchestration strategy reached apply-failed after killing '{process_to_kill}'")

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
    pkill_keywords = PkillKeywords(ssh_connection)

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()

    def teardown() -> None:
        """Cleanup kubernetes upgrade."""
        get_logger().log_teardown_step("Cleanup kubernetes upgrade")
        try:
            kube_upgrade_keywords.kube_upgrade_abort()
        except Exception:
            get_logger().log_info("No upgrade to abort")

    request.addfinalizer(teardown)

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
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    kubelet_failed = _kill_process_until_host_upgrade_status(pkill_keywords, kube_host_upgrade_list_keywords, process_to_kill, target_hostname, "upgrading-kubelet-failed", timeout=600)
    validate_equals(kubelet_failed, True, f"Kubelet upgrade on '{target_hostname}' reached upgrading-kubelet-failed after killing '{process_to_kill}'")
