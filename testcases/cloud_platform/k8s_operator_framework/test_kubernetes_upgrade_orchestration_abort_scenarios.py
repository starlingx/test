"""
Validate Kubernetes upgrade abort scenarios.

Prerequisites
- Need to be run on simplex lab with n-1 kubernetes version
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none, validate_str_contains
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


def _abort_during_kube_upgrade_step(
    request: FixtureRequest,
    step_name: str,
    timeout: int = 900,
    expect_rejected: bool = False,
    expected_error: str = "",
) -> None:
    """Drive a kube upgrade orchestration strategy to a step and abort it.

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
        step_name (str): The orchestration step to wait for before aborting.
        timeout (int): Maximum wait time in seconds for the step to be reached.
        expect_rejected (bool): When True, the abort must be rejected rather than succeed.
        expected_error (str): Substring expected in the abort-rejection message. Required
            (and only used) when ``expect_rejected`` is True.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()
    get_logger().log_info("Kubernetes upgrade configuration loaded successfully")

    kube_strategy_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)

    def teardown() -> None:
        """Cleanup orchestration strategy."""
        get_logger().log_teardown_step("Cleanup orchestration strategy")
        try:
            kube_strategy_keywords.abort_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to abort")
        try:
            kube_strategy_keywords.delete_kube_upgrade_strategy()
        except Exception:
            get_logger().log_info("No strategy to delete")

    request.addfinalizer(teardown)

    get_logger().log_setup_step("Get active and available Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()

    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found {active_kube_version}")

    available_kube_version = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_version, f"Available Kubernetes versions found {available_kube_version}")

    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_version)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")

    get_logger().log_setup_step("Check target kubernetes version is in available kubernetes list")
    validate_list_contains(target_version, available_kube_version, "Target Kubernetes version is in available kubernetes list")

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_output = kube_strategy_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy (non-blocking)")
    kube_strategy_keywords.apply_kube_upgrade_strategy_without_waiting()

    get_logger().log_test_case_step(f"Wait for strategy to reach '{step_name}' step")
    kube_strategy_keywords.wait_for_kube_upgrade_step(step_name, timeout=timeout)

    if expect_rejected:
        get_logger().log_test_case_step(f"Attempt to abort during '{step_name}' and verify it is rejected")
        error_message = kube_strategy_keywords.abort_kube_upgrade_strategy_with_error()
        validate_str_contains(error_message, expected_error, "Abort is rejected with the expected message")

        get_logger().log_test_case_step("Wait for the strategy to finish applying (abort not permitted at this stage)")
        kube_strategy_keywords.wait_for_applied(timeout=timeout)

        get_logger().log_test_case_step("Delete the Kubernetes upgrade strategy")
        kube_strategy_keywords.delete_kube_upgrade_strategy()
        return

    get_logger().log_test_case_step("Abort the Kubernetes upgrade strategy")
    abort_output = kube_strategy_keywords.abort_kube_upgrade_strategy()
    validate_equals(abort_output.is_aborted(), True, "Strategy is in aborted state")
    get_logger().log_info("Kubernetes upgrade strategy aborted successfully")

    get_logger().log_test_case_step("Delete the Kubernetes upgrade strategy")
    kube_strategy_keywords.delete_kube_upgrade_strategy()

    get_logger().log_test_case_step(f"Verify Kubernetes version is still {active_kube_version}")
    current_active_version = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(current_active_version, active_kube_version, "Kubernetes version remains unchanged after abort")

    get_logger().log_test_case_step("Wait for alarms to be cleared, excluding 'Kubernetes upgrade in progress' alarm")
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(["900.007"])


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_download_images(request: FixtureRequest) -> None:
    """Test aborting Kubernetes upgrade orchestration during the downloading images step.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-upgrade-download-images' step
        - Abort the strategy and verify abort succeeded
        - Delete the strategy
        - Verify the Kubernetes version is still the original active version
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(request, "kube-upgrade-download-images")


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_pre_application_update(request: FixtureRequest) -> None:
    """Test aborting Kubernetes upgrade orchestration during the pre application update step.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-pre-application-update' step
        - Abort the strategy and verify abort succeeded
        - Delete the strategy
        - Verify the Kubernetes version is still the original active version
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(request, "kube-pre-application-update")


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_networking(request: FixtureRequest) -> None:
    """Test aborting Kubernetes upgrade orchestration during the upgrade networking step.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-upgrade-networking' step
        - Abort the strategy and verify abort succeeded
        - Delete the strategy
        - Verify the Kubernetes version is still the original active version
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(request, "kube-upgrade-networking")


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_storage(request: FixtureRequest) -> None:
    """Test aborting Kubernetes upgrade orchestration during the upgrade storage step.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-upgrade-storage' step
        - Abort the strategy and verify abort succeeded
        - Delete the strategy
        - Verify the Kubernetes version is still the original active version
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(request, "kube-upgrade-storage")


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_host_cordon(request: FixtureRequest) -> None:
    """Test aborting Kubernetes upgrade orchestration during the host cordon step.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-host-cordon' step
        - Abort the strategy and verify abort succeeded
        - Delete the strategy
        - Verify the Kubernetes version is still the original active version
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(request, "kube-host-cordon")


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_control_plane(request: FixtureRequest) -> None:
    """Test aborting Kubernetes upgrade orchestration during the control-plane upgrade step.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-host-upgrade-control-plane' step
        - Abort the strategy and verify abort succeeded
        - Delete the strategy
        - Verify the Kubernetes version is still the original active version
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(request, "kube-host-upgrade-control-plane", timeout=900)


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_kubelet(request: FixtureRequest) -> None:
    """Test aborting Kubernetes upgrade orchestration during the kubelet upgrade step.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-host-upgrade-kubelet' step
        - Abort the strategy and verify abort succeeded
        - Delete the strategy
        - Verify the Kubernetes version is still the original active version
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(request, "kube-host-upgrade-kubelet", timeout=900)


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_host_uncordon(request: FixtureRequest) -> None:
    """Test aborting Kubernetes upgrade orchestration during the host uncordon step.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-host-uncordon' step
        - Abort the strategy and verify abort succeeded
        - Delete the strategy
        - Verify the Kubernetes version is still the original active version
        - Wait for all alarms to clear

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(request, "kube-host-uncordon")


@mark.p2
@mark.lab_is_simplex
def test_kube_upgrade_orchestration_abort_during_post_application_update(request: FixtureRequest) -> None:
    """Test that aborting Kubernetes upgrade orchestration during post application update is rejected.

    Test Steps:
        - Create orchestration strategy for the target version
        - Apply the strategy (non-blocking)
        - Wait for the strategy to reach the 'kube-post-application-update' step
        - Attempt to abort the strategy and verify the abort is rejected
        - Wait for the strategy to finish applying
        - Delete the strategy

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    _abort_during_kube_upgrade_step(
        request,
        "kube-post-application-update",
        expect_rejected=True,
        expected_error="cannot abort during kube-post-application-update stage",
    )
