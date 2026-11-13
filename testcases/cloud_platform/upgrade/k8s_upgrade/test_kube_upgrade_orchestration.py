from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_keywords import SwManagerKubeUpgradeStrategyKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_upgrade_strategy_timing_keywords import SwManagerKubeUpgradeStrategyTimingKeywords
from keywords.cloud_platform.system.health_query.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords
from keywords.cloud_platform.system.kubernetes.kube_upgrade_show_keywords import KubeUpgradeShowKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords


@mark.p0
def test_kubernetes_upgrade(request: FixtureRequest) -> None:
    """Test Kubernetes upgrade orchestration on standalone lab or dc system controller.

    This test performs Kubernetes upgrade orchestration for any standalone lab or dc system controller.
    It uses sw-manager kube-upgrade-strategy to orchestrate the upgrade, validates the target version
    is available, creates and applies the strategy, then verifies the upgrade completed successfully.

    Test Steps:
        - Setup SSH connection to active controller
        - Check the system is healthy for Kubernetes upgrade
        - Guard against an upgrade already in progress (auto-apply)
        - Get active and available Kubernetes versions
        - Determine target version from config or pick the highest available
        - Validate target version is in the available list
        - Resolve instance-action (force stop-start on simplex when migrate is requested)
        - Create Kubernetes upgrade orchestration strategy
        - Apply the strategy and wait for completion
        - Extract and log upgrade timings
        - Save KPI data to database
        - Verify target version is active on all hosts
        - Verify every host upgraded (control-plane and kubelet) via kube-host-upgrade-list

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
    kube_upgrade_show_keywords = KubeUpgradeShowKeywords(ssh_connection)
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    timing_keywords = SwManagerKubeUpgradeStrategyTimingKeywords()

    def cleanup_strategy() -> None:
        """Cleanup function to ensure strategy is deleted after test completion."""
        get_logger().log_teardown_step("Delete orchestration strategy")
        kube_upgrade_keywords.delete_kube_upgrade_strategy()

    request.addfinalizer(cleanup_strategy)

    # Step 1: Confirm the system is healthy before starting the upgrade.
    get_logger().log_test_case_step("Check the system is healthy for Kubernetes upgrade")
    SystemHealthQueryKeywords(ssh_connection).is_system_healthy_for_kube_upgrade()

    # Step 2: Guard against an upgrade the platform already started itself. On some systems
    # the Kubernetes upgrade runs on auto-apply, where the strategy is created and applied
    # with no operator action. In that state creating a new strategy fails with
    # "409 strategy already exists", and deleting it would abort an in-flight upgrade
    # mid-kubelet. If an upgrade is already in progress, fail fast rather than disrupting it.
    get_logger().log_test_case_step("Check no Kubernetes upgrade is already in progress")
    if kube_upgrade_show_keywords.is_kube_upgrade_in_progress():
        raise Exception("A Kubernetes upgrade is already in progress - not creating a new strategy. Monitor the existing upgrade to completion instead.")

    # Step 3: Query the system for current Kubernetes version information
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

    # Step 4: Validate the target version is actually available for upgrade
    get_logger().log_test_case_step("Check target kubernetes version is in available kubernetes list")
    validate_list_contains(target_version, available_kube_version, "Target Kubernetes version is in available kubernetes list")

    # Step 5: Resolve instance-action, guarding against 'migrate' on a simplex system.
    # 'migrate' is invalid on a single-controller system - sw-manager rejects it with
    # "cannot migrate instances in a single controller configuration" because there is no
    # peer host to move VMs to. On simplex, force 'stop-start'.
    instance_action = kubernetes_upgrade_config.get_instance_action()
    system_mode = SystemShowKeywords(ssh_connection).system_show().get_system_show_object().get_system_mode()
    get_logger().log_info(f"System mode: {system_mode}")
    if system_mode == "simplex" and instance_action == "migrate":
        get_logger().log_info("Simplex system detected with instance_action 'migrate' - overriding to 'stop-start' (migrate is invalid on a single-controller configuration)")
        instance_action = "stop-start"

    # Step 6: Create the orchestration strategy for the target version
    get_logger().log_test_case_step(f"Create Kubernetes upgrade strategy for version {target_version}")
    create_kube_upgrade_output = kube_upgrade_keywords.create_sw_manager_kube_upgrade_strategy(
        target_kube_version=target_version,
        controller_apply_type=kubernetes_upgrade_config.get_controller_apply_type(),
        storage_apply_type=kubernetes_upgrade_config.get_storage_apply_type(),
        worker_apply_type=kubernetes_upgrade_config.get_worker_apply_type(),
        instance_action=instance_action,
        alarm_restrictions=kubernetes_upgrade_config.get_alarm_restrictions(),
        max_parallel_worker_hosts=kubernetes_upgrade_config.get_max_parallel_worker_hosts(),
    )
    validate_equals(create_kube_upgrade_output.get_state(), "ready-to-apply", "Strategy is ready to apply")
    get_logger().log_info("Kubernetes upgrade strategy created successfully and is ready to apply")

    # Step 7: Apply the strategy and wait for the upgrade to complete
    get_logger().log_test_case_step("Apply Kubernetes upgrade strategy")
    apply_output = kube_upgrade_keywords.apply_kube_upgrade_strategy()
    validate_equals(apply_output.get_state(), "applied", "Strategy should be applied")
    get_logger().log_info("Kubernetes upgrade strategy applied successfully")

    # Step 8: Extract timing details from the completed strategy
    get_logger().log_test_case_step("Extract and log upgrade timings")
    details_strategy_output = kube_upgrade_keywords.show_kube_upgrade_strategy_details()
    timings = timing_keywords.extract_kube_upgrade_strategy_timings(details_strategy_output, active_kube_version, target_version)
    formatted_timings = timing_keywords.format_upgrade_timings(timings, active_kube_version, target_version)
    get_logger().log_info(formatted_timings)

    # Step 9: Persist KPI metrics to the database for tracking
    get_logger().log_test_case_step("Save Kubernetes upgrade KPI to database")
    timing_keywords.save_kube_upgrade_kpi_to_database(timings, active_kube_version, target_version)

    # Step 10: Verify the upgrade completed by checking the active version.
    # get_active_kubernetes_version() returns the version whose state is 'active', so a
    # version still reported as 'partial' is excluded - the upgrade is only done once the
    # target version is 'active', not 'partial'.
    get_logger().log_test_case_step(f"Verify target version {target_version} is active on all hosts")
    active_kube_versions = system_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
    validate_equals(active_kube_versions, target_version, "Target version is active on all hosts")
    get_logger().log_info(f"Kubernetes upgrade to {target_version} completed successfully")

    # Step 11: Verify every host upgraded via kube-host-upgrade-list. The upgrade is only
    # complete when every host shows the target in BOTH control_plane_version and
    # kubelet_version - the active-version check alone does not prove per-host completion.
    get_logger().log_test_case_step("Verify every host upgraded via kube-host-upgrade-list")
    # Iterate the kube-host-upgrade-list entries directly so every host is covered and labs
    # without worker nodes (e.g. simplex) need no special handling.
    host_upgrades = kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_kube_host_upgrade_list()
    for host_upgrade in host_upgrades:
        hostname = host_upgrade.get_hostname()
        # Only controllers run a control-plane; every host runs a kubelet.
        if host_upgrade.get_personality() == "controller":
            validate_equals(host_upgrade.get_control_plane_version(), target_version, f"{hostname} control-plane upgraded")
        validate_equals(host_upgrade.get_kubelet_version(), target_version, f"{hostname} kubelet upgraded")
