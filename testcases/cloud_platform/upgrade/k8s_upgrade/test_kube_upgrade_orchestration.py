from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_timing_keywords import SwManagerKubeUpgradeStrategyTimingKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


@mark.p0
def test_kubernetes_upgrade(request: FixtureRequest) -> None:
    """Test Kubernetes upgrade orchestration on standalone lab or dc system controller.

    This test performs Kubernetes upgrade orchestration for any standalone lab or dc system controller.

    Test Steps:
        - Setup SSH connection
        - Validate Kubernetes versions
        - Create and apply Kubernetes upgrade strategy
        - Verify upgrade completion and cleanup

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    k8s_config = ConfigurationManager.get_k8s_config()

    kube_upgrade_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    timing_keywords = SwManagerKubeUpgradeStrategyTimingKeywords()

    def cleanup_strategy() -> None:
        """Cleanup function to ensure strategy is deleted."""
        get_logger().log_teardown_step("Delete orchestration strategy")
        kube_upgrade_keywords.delete_kube_upgrade_strategy()

    request.addfinalizer(cleanup_strategy)

    get_logger().log_test_case_step("Get Active, available and target Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found {active_kube_version}")
    available_kube_version = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_version, f"Available Kubernetes versions found {available_kube_version}")
    target_version = k8s_config.get_k8_target_version()
    get_logger().log_info(f"Target kubernetes version is {target_version}")

    get_logger().log_test_case_step("Check target kubernetes version is in available kubernetes list")
    validate_list_contains(target_version, available_kube_version, "Target Kubernetes version is in available kubernetes list")

    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_kube_upgrade_output = kube_upgrade_keywords.create_sw_manager_kube_upgrade_strategy(target_kube_version=target_version)
    validate_equals(create_kube_upgrade_output.get_state(), "ready-to-apply", "Strategy is ready to apply")

    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy")
    apply_output = kube_upgrade_keywords.apply_kube_upgrade_strategy()
    validate_equals(apply_output.get_state(), "applied", "Strategy should be applied")

    get_logger().log_test_case_step("Extract and log upgrade timings")
    details_strategy_output = kube_upgrade_keywords.show_kube_upgrade_strategy_details()
    timings = timing_keywords.extract_kube_upgrade_strategy_timings(details_strategy_output, active_kube_version, target_version)
    formatted_timings = timing_keywords.format_upgrade_timings(timings, active_kube_version, target_version)
    get_logger().log_info(formatted_timings)

    get_logger().log_test_case_step(f"Verify target version {target_version} is active on all hosts")
    active_kube_versions = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(active_kube_versions, target_version, "Target version is active on all hosts")
