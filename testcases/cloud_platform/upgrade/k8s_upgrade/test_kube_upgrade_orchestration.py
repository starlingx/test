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
    It uses sw-manager kube-upgrade-strategy to orchestrate the upgrade, validates the target version
    is available, creates and applies the strategy, then verifies the upgrade completed successfully.

    Test Steps:
        - Setup SSH connection to active controller
        - Get active and available Kubernetes versions
        - Determine target version from config or pick the highest available
        - Validate target version is in the available list
        - Create Kubernetes upgrade orchestration strategy
        - Apply the strategy and wait for completion
        - Extract and log upgrade timings
        - Save KPI data to database
        - Verify target version is active on all hosts

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.

    Raises:
        AssertionError: If any validation step fails.
    """
    # Establish SSH connection to the active controller
    get_logger().log_info("Establishing SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Load the kubernetes upgrade configuration (target version, subcloud settings)
    kubernetes_upgrade_config = ConfigurationManager.get_kubernetes_upgrade_config()
    get_logger().log_info("Kubernetes upgrade configuration loaded successfully")

    # Initialize keywords for strategy management and version queries
    kube_upgrade_keywords = SwManagerKubeUpgradeStrategyKeywords(ssh_connection)
    system_kube_keywords = SystemKubernetesListKeywords(ssh_connection)
    timing_keywords = SwManagerKubeUpgradeStrategyTimingKeywords()

    def cleanup_strategy() -> None:
        """Cleanup function to ensure strategy is deleted after test completion."""
        get_logger().log_teardown_step("Delete orchestration strategy")
        kube_upgrade_keywords.delete_kube_upgrade_strategy()

    request.addfinalizer(cleanup_strategy)

    # Step 1: Query the system for current Kubernetes version information
    get_logger().log_test_case_step("Get Active, available and target Kubernetes versions")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()

    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found {active_kube_version}")
    get_logger().log_info(f"Current active Kubernetes version: {active_kube_version}")

    available_kube_version = kube_version_list.get_version_by_state("available")
    validate_not_none(available_kube_version, f"Available Kubernetes versions found {available_kube_version}")
    get_logger().log_info(f"Available Kubernetes versions for upgrade: {available_kube_version}")

    # Determine target version: use config value if set, otherwise pick the highest available
    target_version = kubernetes_upgrade_config.resolve_target_version(available_kube_version)
    get_logger().log_info(f"Resolved target Kubernetes version: {target_version}")

    # Step 2: Validate the target version is actually available for upgrade
    get_logger().log_test_case_step("Check target kubernetes version is in available kubernetes list")
    validate_list_contains(target_version, available_kube_version, "Target Kubernetes version is in available kubernetes list")

    # Step 3: Create the orchestration strategy for the target version
    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_kube_upgrade_output = kube_upgrade_keywords.create_sw_manager_kube_upgrade_strategy(
        target_kube_version=target_version,
        controller_apply_type=kubernetes_upgrade_config.get_controller_apply_type(),
        storage_apply_type=kubernetes_upgrade_config.get_storage_apply_type(),
        worker_apply_type=kubernetes_upgrade_config.get_worker_apply_type(),
        instance_action=kubernetes_upgrade_config.get_instance_action(),
        alarm_restrictions=kubernetes_upgrade_config.get_alarm_restrictions(),
        max_parallel_worker_hosts=kubernetes_upgrade_config.get_max_parallel_worker_hosts(),
    )
    validate_equals(create_kube_upgrade_output.get_state(), "ready-to-apply", "Strategy is ready to apply")
    get_logger().log_info("Kubernetes upgrade strategy created successfully and is ready to apply")

    # Step 4: Apply the strategy and wait for the upgrade to complete
    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy")
    apply_output = kube_upgrade_keywords.apply_kube_upgrade_strategy()
    validate_equals(apply_output.get_state(), "applied", "Strategy should be applied")
    get_logger().log_info("Kubernetes upgrade strategy applied successfully")

    # Step 5: Extract timing details from the completed strategy
    get_logger().log_test_case_step("Extract and log upgrade timings")
    details_strategy_output = kube_upgrade_keywords.show_kube_upgrade_strategy_details()
    timings = timing_keywords.extract_kube_upgrade_strategy_timings(details_strategy_output, active_kube_version, target_version)
    formatted_timings = timing_keywords.format_upgrade_timings(timings, active_kube_version, target_version)
    get_logger().log_info(formatted_timings)

    # Step 6: Persist KPI metrics to the database for tracking
    get_logger().log_test_case_step("Save Kubernetes upgrade KPI to database")
    timing_keywords.save_kube_upgrade_kpi_to_database(timings, active_kube_version, target_version)

    # Step 7: Verify the upgrade completed by checking the active version
    get_logger().log_test_case_step(f"Verify target version {target_version} is active on all hosts")
    active_kube_versions = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(active_kube_versions, target_version, "Target version is active on all hosts")
    get_logger().log_info(f"Kubernetes upgrade to {target_version} completed successfully")
