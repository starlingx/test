import time

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.linux.pkill.pkill_keywords import PkillKeywords


def _kill_process_until_apply_failed(pkill_keywords: PkillKeywords, kube_strategy_keywords: SwManagerKubeUpgradeStrategyKeywords, process_pattern: str, timeout: int = 1800) -> bool:
    """Kill a process in a loop until the orchestration strategy state reaches apply-failed.

    Args:
        pkill_keywords (PkillKeywords): Keywords for killing processes.
        kube_strategy_keywords (SwManagerKubeUpgradeStrategyKeywords): Keywords for sw-manager kube-upgrade-strategy commands.
        process_pattern (str): Process pattern to kill.
        timeout (int): Maximum wait time in seconds.

    Returns:
        bool: True if apply-failed state was reached.
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
            if state == "failed":
                return True
        except Exception:
            get_logger().log_info("sw-manager command failed during polling, retrying")
    return False


@mark.lab_is_simplex
def test_orchestrated_kube_upgrade_fails_on_control_plane_upgrade(request: FixtureRequest) -> None:
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

    k8s_config = ConfigurationManager.get_k8s_config()
    target_version = k8s_config.get_k8_target_version()

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
    validate_list_contains(target_version, available_kube_versions, "Target version is in available list")

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy (non-blocking)")
    kube_strategy_keywords.apply_kube_upgrade_strategy_without_waiting()

    get_logger().log_test_case_step("Wait for strategy to reach control-plane upgrade phase")
    kube_strategy_keywords.wait_for_kube_upgrade_step("kube-host-upgrade-control-plane", timeout=1200)

    get_logger().log_test_case_step(f"Kill '{process_to_kill}' in loop until strategy reaches apply-failed")
    apply_failed = _kill_process_until_apply_failed(pkill_keywords, kube_strategy_keywords, process_to_kill, timeout=1800)
    validate_equals(apply_failed, True, f"Orchestration strategy reached apply-failed after killing '{process_to_kill}'")

    get_logger().log_test_case_step("Verify apply-reason contains upgrading-first-master-failed")
    strategy_obj = kube_strategy_keywords.show_kube_upgrade_strategy().get_swmanager_kube_upgrade_strategy_show()
    apply_reason = strategy_obj.get_apply_reason()
    validate_str_contains(apply_reason, "upgrading-first-master-failed", "Apply reason indicates first master upgrade failure")
