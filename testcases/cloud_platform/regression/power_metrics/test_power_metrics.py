from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals
from keywords.cloud_platform.applications.power_metrics_keywords import CADVISOR_METRICS_ENDPOINT, PowerMetricsKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


def setup_power_metrics(request: FixtureRequest, install: bool = True) -> None:
    """Connect to the lab, optionally ensure power-metrics is applied, and register test cleanup.

    Args:
        request (FixtureRequest): The pytest request used to register the finalizer.
        install (bool): Whether to install power-metrics as a precondition. The install
            and uninstall tests pass False because they drive the application lifecycle
            themselves.
    """
    get_logger().log_setup_step(f"Connecting to lab: {ConfigurationManager.get_lab_config().get_lab_name()}")
    power_metrics_keywords = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    if install:
        if power_metrics_keywords.is_power_metrics_already_applied():
            get_logger().log_info(f"{power_metrics_keywords.get_app_name()} is already applied, tearing down.")
            power_metrics_keywords.remove_power_metrics()

        get_logger().log_setup_step(f"Installing {power_metrics_keywords.get_app_name()} application")
        power_metrics_keywords.ensure_power_metrics_applied()

    def cleanup() -> None:
        power_metrics_keywords.remove_power_metrics()
        get_logger().log_teardown_step("Disconnecting from lab")
        SSHConnectionManager.remove_all()

    request.addfinalizer(cleanup)


# ============================================================================
# Power Metrics - Install and uninstall application
# ============================================================================


@mark.p0
def test_power_metrics_install_and_uninstall(request: FixtureRequest) -> None:
    """
    Power Metrics - Install and uninstall application

    Test Steps:
        1. Check if power-metrics is already uninstalled, and uninstall it if it is not
        2. Label the nodes, upload, and apply the power-metrics application
        3. Verify power-metrics reaches the applied status
        4. Verify telegraf and cAdvisor pods are running
        5. Verify metrics are being collected on all nodes
        6. Remove and delete the power-metrics application
        7. Verify power-metrics is not present in the application list
        8. Verify telegraf pods are no longer running
    """
    setup_power_metrics(request, install=False)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is already uninstalled, and uninstall it if it is not")
    if power_metrics.is_power_metrics_installed():
        get_logger().log_info(f"{power_metrics.get_app_name()} is still installed, uninstalling it first")
        power_metrics.remove_power_metrics()
    else:
        get_logger().log_info(f"{power_metrics.get_app_name()} is already uninstalled, proceeding with the install")

    get_logger().log_test_case_step("Label the nodes, upload, and apply the power-metrics application")
    power_metrics.ensure_power_metrics_applied()

    get_logger().log_test_case_step("Verify power-metrics reaches the applied status")
    power_metrics.validate_power_metrics_applied()

    get_logger().log_test_case_step("Verify telegraf and cAdvisor pods are running")
    power_metrics.wait_for_telegraf_running()
    power_metrics.wait_for_cadvisor_running()

    get_logger().log_test_case_step("Verify metrics are being collected on all nodes")
    power_metrics.validate_metrics(["powerstat_package_current_power_consumption_watts"], "should be present after install")

    get_logger().log_test_case_step("Remove and delete the power-metrics application")
    power_metrics.remove_power_metrics()

    get_logger().log_test_case_step("Verify power-metrics is not present in the application list")
    validate_equals(power_metrics.is_power_metrics_installed(), False, f"{power_metrics.get_app_name()} should be absent from the application list after uninstall")

    get_logger().log_test_case_step("Verify telegraf pods are no longer running")
    power_metrics.validate_telegraf_not_running()


# ============================================================================
# Power Metrics - Change Helm values - Filter package metrics
# ============================================================================


def test_change_helm_values_filter_package_metrics(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Filter package metrics

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify all package metrics are collected
        3. Update telegraf helm value with only current_power_consumption via filter_package_metrics.yaml
        4. Reapply power-metrics application and wait
        5. Verify that only current_power_consumption metric is shown
        6. Verify that dram, tdp, cpu_base_frequency, uncore_frequency are NOT shown
        7. Delete the user_overrides, reapply, and wait
        8. Verify all package metrics are collected again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_expected = [
        "powerstat_package_current_power_consumption_watts",
    ]

    metrics_not_expected = [
        "powerstat_package_current_dram_power_consumption_watts",
        "powerstat_package_thermal_design_power_watts",
        "powerstat_package_cpu_base_frequency_mhz",
        "powerstat_package_uncore_frequency",
    ]

    all_metrics = metrics_not_expected + metrics_expected
    override_files = ["filter_package_metrics_toml.yaml", "filter_package_metrics.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify all package metrics are collected")
    power_metrics.validate_metrics(all_metrics, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value with only current_power_consumption via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that only current_power_consumption metric is shown")
        power_metrics.validate_metrics(metrics_expected, "should still be present after filter")

        get_logger().log_test_case_step("Verify that dram, tdp, cpu_base_frequency, uncore_frequency are NOT shown")
        power_metrics.validate_metrics(metrics_not_expected, "should NOT be present after filter override", should_be_present=False)

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify all package metrics are collected again")
        power_metrics.validate_metrics(all_metrics, "should be present again after restoring defaults")


# ============================================================================
# Power Metrics - Change Helm values - Empty package metrics
# ============================================================================


def test_change_helm_values_empty_package_metrics(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Empty package metrics

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify all package metrics are collected
        3. Update telegraf helm value with empty package_metrics via empty_package_metrics.yaml
        4. Reapply power-metrics application and wait
        5. Verify that NO package metrics are shown
        6. Delete the user_overrides, reapply, and wait
        7. Verify all package metrics are collected again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_to_check = [
        "powerstat_package_current_power_consumption_watts",
        "powerstat_package_current_dram_power_consumption_watts",
        "powerstat_package_thermal_design_power_watts",
        "powerstat_package_cpu_base_frequency_mhz",
        "powerstat_package_uncore_frequency",
    ]

    override_files = ["empty_package_metrics_toml.yaml", "empty_package_metrics.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify all package metrics are collected")
    power_metrics.validate_metrics(metrics_to_check, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value with empty package_metrics via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that NO package metrics are shown")
        power_metrics.validate_metrics(metrics_to_check, "should NOT be present with empty package_metrics override", should_be_present=False)
        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify all package metrics are collected again")
        power_metrics.validate_metrics(metrics_to_check, "should be present again after restoring defaults")


# ============================================================================
# Power Metrics - Change Helm values - Without package metrics
# ============================================================================


def test_change_helm_values_without_package_metrics(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Without package metrics

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify all package metrics are collected
        3. Update telegraf helm value via without_package_metrics.yaml
        4. Reapply power-metrics application and wait
        5. Verify that default package metrics are still shown
        6. Verify that non default package metrics are not shown
        7. Delete the user_overrides, reapply, and wait
        8. Verify all package metrics are collected again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_expected = [
        "powerstat_package_current_power_consumption_watts",
        "powerstat_package_current_dram_power_consumption_watts",
        "powerstat_package_thermal_design_power_watts",
    ]

    metrics_not_expected = [
        "powerstat_package_cpu_base_frequency_mhz",
        "powerstat_package_uncore_frequency",
    ]

    all_metrics = metrics_not_expected + metrics_expected
    override_files = ["without_package_metrics_toml.yaml", "without_package_metrics.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify all package metrics are collected")
    power_metrics.validate_metrics(all_metrics, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that default package metrics are still shown")
        power_metrics.validate_metrics(metrics_expected, "should still be present after without_package_metrics override")

        get_logger().log_test_case_step("Verify that non default package metrics are not shown")
        power_metrics.validate_metrics(metrics_not_expected, "should NOT be present after filter override", should_be_present=False)

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify all package metrics are collected again")
        power_metrics.validate_metrics(all_metrics, "should be present again after restoring defaults")


# ============================================================================
# Power Metrics - Change Helm values - Filter CPU metrics
# ============================================================================


def test_change_helm_values_filter_cpu_metrics(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Filter CPU metrics

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify all per-CPU metrics are collected
        3. Update telegraf helm value with only cpu_frequency in cpu_metrics via filter_cpu_metrics.yaml
        4. Reapply power-metrics application and wait
        5. Verify that only cpu_frequency metric is shown
        6. Verify that busy_frequency, temperature, c0, c1, c6 are NOT shown
        7. Delete the user_overrides, reapply, and wait
        8. Verify all per-CPU metrics are collected again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_expected = [
        "powerstat_core_cpu_frequency_mhz",
    ]

    metrics_not_expected = [
        "powerstat_core_cpu_busy_frequency_mhz",
        "powerstat_core_cpu_temperature_celsius",
        "powerstat_core_cpu_c0_state_residency_percent",
        "powerstat_core_cpu_c1_state_residency_percent",
        "powerstat_core_cpu_c6_state_residency_percent",
    ]

    all_metrics = metrics_not_expected + metrics_expected
    override_files = ["filter_cpu_metrics_toml.yaml", "filter_cpu_metrics.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify all per-CPU metrics are collected")
    power_metrics.validate_metrics(all_metrics, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value with only cpu_frequency in cpu_metrics via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that only cpu_frequency metric is shown")
        power_metrics.validate_metrics(metrics_expected, "should still be present after filter")

        get_logger().log_test_case_step("Verify that busy_frequency, temperature, c0, c1, c6 are NOT shown")
        power_metrics.validate_metrics(metrics_not_expected, "should NOT be present after filter override", should_be_present=False)

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify all per-CPU metrics are collected again")
        power_metrics.validate_metrics(all_metrics, "should be present again after restoring defaults")


# ============================================================================
# Power Metrics - Change Helm values - Empty CPU metrics
# ============================================================================


def test_change_helm_values_empty_cpu_metrics(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Empty CPU metrics

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify all per-CPU metrics are collected
        3. Update telegraf helm value with empty cpu_metrics via empty_cpu_metrics.yaml
        4. Reapply power-metrics application and wait
        5. Verify that NO per-CPU metrics are shown
        6. Delete the user_overrides, reapply, and wait
        7. Verify all per-CPU metrics are collected again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_to_check = [
        "powerstat_core_cpu_frequency_mhz",
        "powerstat_core_cpu_busy_frequency_mhz",
        "powerstat_core_cpu_temperature_celsius",
        "powerstat_core_cpu_c0_state_residency_percent",
        "powerstat_core_cpu_c1_state_residency_percent",
        "powerstat_core_cpu_c6_state_residency_percent",
    ]

    override_files = ["empty_cpu_metrics_toml.yaml", "empty_cpu_metrics.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify all per-CPU metrics are collected")
    power_metrics.validate_metrics(metrics_to_check, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value with empty cpu_metrics via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that NO per-CPU metrics are shown")
        power_metrics.validate_metrics(metrics_to_check, "should NOT be present with empty cpu_metrics override", should_be_present=False)

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify all per-CPU metrics are collected again")
        power_metrics.validate_metrics(metrics_to_check, "should be present again after restoring defaults")


# ============================================================================
# Power Metrics - Change Helm values - Without CPU metrics
# ============================================================================


def test_change_helm_values_without_cpu_metrics(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Without CPU metrics

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify that per-CPU metrics are collected
        3. Update telegraf helm value via without_cpu_metrics.yaml
        4. Reapply power-metrics application and wait
        5. Verify that no per-CPU metrics are shown
        6. Delete the user_overrides, reapply, and wait
        7. Verify that per-CPU metrics are collected again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_to_check = [
        "powerstat_core_cpu_frequency_mhz",
        "powerstat_core_cpu_busy_frequency_mhz",
        "powerstat_core_cpu_temperature_celsius",
        "powerstat_core_cpu_c0_state_residency_percent",
        "powerstat_core_cpu_c1_state_residency_percent",
        "powerstat_core_cpu_c6_state_residency_percent",
    ]

    override_files = ["without_cpu_metrics_toml.yaml", "without_cpu_metrics.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify that per-CPU metrics are collected")
    power_metrics.validate_metrics(metrics_to_check, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that no per-CPU metrics are shown")
        power_metrics.validate_metrics(metrics_to_check, "should NOT be present with without_cpu_metrics override", should_be_present=False)

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify that per-CPU metrics are collected again")
        power_metrics.validate_metrics(metrics_to_check, "should be present again after restoring defaults")


# ============================================================================
# Power Metrics - Change Helm values - Filter excluded CPUs
# ============================================================================


def test_change_helm_values_filter_excluded_cpus(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Filter excluded CPUs

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify that cpu_frequency is shown for all CPUs
        3. Update telegraf helm value with excluded_cpus via filter_excluded_cpus.yaml
        4. Reapply power-metrics application and wait
        5. Verify that cpu_frequency is shown for included CPUs
        6. Verify that cpu_frequency is NOT shown for excluded CPUs
        7. Delete the user_overrides, reapply, and wait
        8. Verify that cpu_frequency is shown for all CPUs again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    included_cpu_ids = ["0", "1", "2", "3", "8"]
    excluded_cpu_ids = ["4", "5", "6", "7", "9"]
    all_cpu_ids = included_cpu_ids + excluded_cpu_ids
    override_files = ["filter_excluded_cpus_toml.yaml", "filter_excluded_cpus.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
    power_metrics.validate_cpu_ids(all_cpu_ids, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value with excluded_cpus via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that cpu_frequency is shown for kept CPUs")
        power_metrics.validate_cpu_ids(included_cpu_ids, "should still be present after exclusion")

        get_logger().log_test_case_step("Verify that cpu_frequency is NOT shown for excluded CPUs")
        power_metrics.validate_cpu_ids(excluded_cpu_ids, "should NOT be present after exclusion", should_be_present=False)

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify that cpu_frequency is shown for all CPUs again")
        power_metrics.validate_cpu_ids(all_cpu_ids, "should be present after restoring defaults")


# ============================================================================
# Power Metrics - Change Helm values - Filter included CPUs
# ============================================================================


def test_change_helm_values_filter_included_cpus(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Filter included CPUs

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify that cpu_frequency is shown for all CPUs
        3. Update telegraf helm value with included_cpus via filter_included_cpus.yaml
        4. Reapply power-metrics application and wait
        5. Verify that cpu_frequency is shown for included CPUs
        6. Verify that cpu_frequency is NOT shown for excluded CPUs
        7. Delete the user_overrides, reapply, and wait
        8. Verify that cpu_frequency is shown for all CPUs again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    included_cpu_ids = ["0", "1", "2", "3", "5", "6", "8"]
    excluded_cpu_ids = ["4", "7", "9"]
    all_cpu_ids = included_cpu_ids + excluded_cpu_ids
    override_files = ["filter_included_cpus_toml.yaml", "filter_included_cpus.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
    power_metrics.validate_cpu_ids(all_cpu_ids, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value with included_cpus via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that cpu_frequency is shown for included CPUs")
        power_metrics.validate_cpu_ids(included_cpu_ids, "should still be present after inclusion filter")

        get_logger().log_test_case_step("Verify that cpu_frequency is NOT shown for excluded CPUs")
        power_metrics.validate_cpu_ids(excluded_cpu_ids, "should NOT be present after inclusion filter", should_be_present=False)

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify that cpu_frequency is shown for all CPUs again")
        power_metrics.validate_cpu_ids(all_cpu_ids, "should be present after restoring defaults")


# ============================================================================
# Power Metrics - Change Helm values - Empty excluded CPUs
# ============================================================================


def test_change_helm_values_empty_excluded_cpus(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Empty excluded CPUs empty

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify that cpu_frequency is shown for all CPUs
        3. Update telegraf helm value with empty excluded_cpus via excluded_cpus_empty.yaml
        4. Reapply power-metrics application and wait
        5. Verify that cpu_frequency remains shown for all CPUs (empty means no exclusion)
        6. Delete the user_overrides, reapply, and wait
        7. Verify that cpu_frequency is shown for all CPUs
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_to_check = ["powerstat_core_cpu_frequency_mhz"]
    override_files = ["excluded_cpus_empty_toml.yaml", "excluded_cpus_empty.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
    power_metrics.validate_metrics(metrics_to_check, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value with empty excluded_cpus via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that cpu_frequency remains shown for all CPUs (empty means no exclusion)")
        power_metrics.validate_metrics(metrics_to_check, "should remain present with empty excluded_cpus")

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
        power_metrics.validate_metrics(metrics_to_check, "should be present after restore")


# ============================================================================
# Power Metrics - Change Helm values - Empty included CPUs
# ============================================================================


def test_change_helm_values_included_empty_cpus(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Empty included CPUs

    This test is executed with both toml and config override files.

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify that cpu_frequency is shown for all CPUs
        3. Update telegraf helm value with empty included_cpus via included_cpus_empty.yaml
        4. Reapply power-metrics application and wait
        5. Verify that cpu_frequency remains shown for all CPUs (empty means all included)
        6. Delete the user_overrides, reapply, and wait
        7. Verify that cpu_frequency is shown for all CPUs
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_to_check = ["powerstat_core_cpu_frequency_mhz"]
    override_files = ["included_cpus_empty_toml.yaml", "included_cpus_empty.yaml"]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
    power_metrics.validate_metrics(metrics_to_check, "should be present before override")
    for override_file in override_files:
        get_logger().log_test_case_step(f"Update telegraf helm value with empty included_cpus via {override_file}")
        power_metrics.upload_and_apply_helm_override(override_file)

        get_logger().log_test_case_step("Reapply power-metrics application and wait")
        power_metrics.apply_power_metrics()
        power_metrics.wait_for_telegraf_running()

        get_logger().log_test_case_step("Verify that cpu_frequency remains shown for all CPUs (empty means all included)")
        power_metrics.validate_metrics(metrics_to_check, "should remain present with empty included_cpus")

        get_logger().log_test_case_step("Delete the user_overrides, reapply, and wait")
        power_metrics.delete_override_and_reapply()

        get_logger().log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
        power_metrics.validate_metrics(metrics_to_check, "should be present after restore")


# ============================================================================
# Power Metrics - Change Helm values - Disable and Enable Telegraf
# ============================================================================


@mark.p0
@mark.lab_has_linux_cpu_metrics
def test_change_helm_values_disable_and_enable_telegraf(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Disable and Enable Telegraf

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify metrics are being collected
        3. Disable telegraf via telegraf_disabled.yaml override
        4. Reapply power-metrics application
        5. Verify that telegraf pod is NOT running
        6. Verify that no telegraf metrics are shown
        7. Enable telegraf via telegraf_enabled.yaml override
        8. Reapply power-metrics application and wait
        9. Verify that metrics are shown once again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_to_check = [
        "powerstat_package_cpu_base_frequency_mhz",
        "powerstat_package_current_power_consumption_watts",
        "linux_cpu_cpuinfo_min_freq",
    ]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify metrics are being collected")
    power_metrics.validate_metrics(metrics_to_check, "should be present before disabling telegraf")

    get_logger().log_test_case_step("Disable telegraf via telegraf_disabled.yaml override")
    power_metrics.upload_and_apply_helm_override("telegraf_disabled.yaml")

    get_logger().log_test_case_step("Reapply power-metrics application")
    power_metrics.apply_power_metrics()

    get_logger().log_test_case_step("Verify that telegraf pod is NOT running")
    power_metrics.validate_telegraf_not_running()

    get_logger().log_test_case_step("Verify that no telegraf metrics are shown")
    power_metrics.validate_metrics(metrics_to_check, "should NOT be present after disabling telegraf", should_be_present=False)

    get_logger().log_test_case_step("Enable telegraf via telegraf_enabled.yaml override")
    power_metrics.upload_and_apply_helm_override("telegraf_enabled.yaml")

    get_logger().log_test_case_step("Reapply power-metrics application and wait")
    power_metrics.apply_power_metrics()
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify that metrics are shown once again")
    power_metrics.validate_metrics(metrics_to_check, "should be present again after re-enabling telegraf")


# ============================================================================
# Power Metrics - Change Helm values - Disable and Enable cAdvisor
# ============================================================================


def test_change_helm_values_disable_and_enable_cadvisor(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Disable and Enable cAdvisor

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify cAdvisor metrics are being collected
        3. Disable cAdvisor via cadvisor_disabled.yaml override
        4. Reapply power-metrics application and wait
        5. Verify that no cAdvisor metrics are shown
        6. Enable cAdvisor via cadvisor_enabled.yaml override
        7. Reapply power-metrics application and wait
        8. Verify that cAdvisor metrics are shown once again
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_cadvisor_running()

    get_logger().log_test_case_step("Verify cAdvisor metrics are being collected")
    power_metrics.validate_metrics(["container_memory_rss"], "should be present before disabling cAdvisor", endpoint=CADVISOR_METRICS_ENDPOINT, grep_pattern="container_memory_rss", max_lines=50)

    get_logger().log_test_case_step("Disable cAdvisor via cadvisor_disabled.yaml override")
    power_metrics.upload_and_apply_helm_override("cadvisor_disabled.yaml", chart_name="cadvisor")

    get_logger().log_test_case_step("Reapply power-metrics application and wait")
    power_metrics.apply_power_metrics()

    get_logger().log_test_case_step("Verify that no cAdvisor metrics are shown")
    power_metrics.validate_metrics(["container_memory_rss"], "should NOT be present after disabling cAdvisor", should_be_present=False, endpoint=CADVISOR_METRICS_ENDPOINT, grep_pattern="container_memory_rss", max_lines=50)

    get_logger().log_test_case_step("Enable cAdvisor via cadvisor_enabled.yaml override")
    power_metrics.upload_and_apply_helm_override("cadvisor_enabled.yaml", chart_name="cadvisor")

    get_logger().log_test_case_step("Reapply power-metrics application and wait")
    power_metrics.apply_power_metrics()
    power_metrics.wait_for_cadvisor_running()

    get_logger().log_test_case_step("Verify that cAdvisor metrics are shown once again")
    power_metrics.validate_metrics(["container_memory_rss"], "should be present again after re-enabling cAdvisor", endpoint=CADVISOR_METRICS_ENDPOINT, grep_pattern="container_memory_rss", max_lines=50)


# ============================================================================
# Power Metrics - Per-cpu current temperature (Celsius)
# ============================================================================


def test_metric_per_cpu_current_temperature(request: FixtureRequest) -> None:
    """
    Power Metrics - Per-cpu current temperature (Celsius)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_core_cpu_temperature_celsius metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_core_cpu_temperature_celsius metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_core_cpu_temperature_celsius"], "should be present")


# ============================================================================
# Power Metrics - Per-cpu percentage in c6 state (%)
# ============================================================================


def test_metric_per_cpu_percentage_c6_state(request: FixtureRequest) -> None:
    """
    Power Metrics - Per-cpu percentage in c6 state (%)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_core_cpu_c6_state_residency_percent metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_core_cpu_c6_state_residency_percent metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_core_cpu_c6_state_residency_percent"], "should be present")


# ============================================================================
# Power Metrics - Per-cpu percentage in c1 state (%)
# ============================================================================


def test_metric_per_cpu_percentage_c1_state(request: FixtureRequest) -> None:
    """
    Power Metrics - Per-cpu percentage in c1 state (%)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_core_cpu_c1_state_residency_percent metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_core_cpu_c1_state_residency_percent metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_core_cpu_c1_state_residency_percent"], "should be present")


# ============================================================================
# Power Metrics - Per-cpu percentage in c0 state (%)
# ============================================================================


def test_metric_per_cpu_percentage_c0_state(request: FixtureRequest) -> None:
    """
    Power Metrics - Per-cpu percentage in c0 state (%)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_core_cpu_c0_state_residency_percent metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_core_cpu_c0_state_residency_percent metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_core_cpu_c0_state_residency_percent"], "should be present")


# ============================================================================
# Power Metrics - Per-cpu busy frequency (mhz)
# ============================================================================


def test_metric_per_cpu_busy_frequency(request: FixtureRequest) -> None:
    """
    Power Metrics - Per-cpu busy frequency (mhz)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_core_cpu_busy_frequency_mhz metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_core_cpu_busy_frequency_mhz metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_core_cpu_busy_frequency_mhz"], "should be present")


# ============================================================================
# Power Metrics - Per-cpu current frequency (mhz)
# ============================================================================


@mark.p0
@mark.lab_has_linux_cpu_metrics
def test_metric_per_cpu_current_frequency(request: FixtureRequest) -> None:
    """
    Power Metrics - Per-cpu current frequency (mhz)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify linux_cpu_scaling_cur_freq metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify linux_cpu_scaling_cur_freq metric is present on all nodes")
    power_metrics.validate_metrics(["linux_cpu_scaling_cur_freq"], "should be present")


# ============================================================================
# Power Metrics - Per-cpu maximum frequency setting (mhz)
# ============================================================================


@mark.p0
@mark.lab_has_linux_cpu_metrics
def test_metric_per_cpu_maximum_frequency_setting(request: FixtureRequest) -> None:
    """
    Power Metrics - Per-cpu maximum frequency setting (mhz)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify linux_cpu_cpuinfo_max_freq metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify linux_cpu_cpuinfo_max_freq metric is present on all nodes")
    power_metrics.validate_metrics(["linux_cpu_cpuinfo_max_freq"], "should be present")


# ============================================================================
# Power Metrics - Per-cpu minimum frequency setting (mhz)
# ============================================================================


@mark.p0
@mark.lab_has_linux_cpu_metrics
def test_metric_per_cpu_minimum_frequency_setting(request: FixtureRequest) -> None:
    """
    Power Metrics - Per-cpu minimum frequency setting (mhz)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify linux_cpu_cpuinfo_min_freq metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify linux_cpu_cpuinfo_min_freq metric is present on all nodes")
    power_metrics.validate_metrics(["linux_cpu_cpuinfo_min_freq"], "should be present")


# ============================================================================
# Power Metrics - Uncore frequency setting (mhz)
# ============================================================================


def test_metric_uncore_frequency_setting(request: FixtureRequest) -> None:
    """
    Power Metrics - Uncore frequency setting (mhz)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_package_uncore_frequency metrics are present on all nodes
        3. Verify cur, max, and min uncore frequency sub-metrics are present
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    metrics_to_check = [
        "powerstat_package_uncore_frequency_mhz_cur",
        "powerstat_package_uncore_frequency_limit_mhz_max",
        "powerstat_package_uncore_frequency_limit_mhz_min",
    ]

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_package_uncore_frequency metrics are present on all nodes")
    power_metrics.validate_metrics(metrics_to_check, "should be present")


# ============================================================================
# Power Metrics - Cpu base frequency setting (mhz)
# ============================================================================


def test_metric_cpu_base_frequency_setting(request: FixtureRequest) -> None:
    """
    Power Metrics - Cpu base frequency setting (mhz)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_package_cpu_base_frequency_mhz metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_package_cpu_base_frequency_mhz metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_package_cpu_base_frequency_mhz"], "should be present")


# ============================================================================
# Power Metrics - Dram power consumption (watts)
# ============================================================================


def test_metric_dram_power_consumption(request: FixtureRequest) -> None:
    """
    Power Metrics - Dram power consumption (watts)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_package_current_dram_power_consumption_watts metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_package_current_dram_power_consumption_watts metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_package_current_dram_power_consumption_watts"], "should be present")


# ============================================================================
# Power Metrics - Current processor package power consumption (watts)
# ============================================================================


def test_metric_current_processor_package_power_consumption(request: FixtureRequest) -> None:
    """
    Power Metrics - Current processor package power consumption (watts)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_package_current_power_consumption_watts metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_package_current_power_consumption_watts metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_package_current_power_consumption_watts"], "should be present")


# ============================================================================
# Power Metrics - Thermal Design Power (TDP) power setting (watts)
# ============================================================================


def test_metric_thermal_design_power_setting(request: FixtureRequest) -> None:
    """
    Power Metrics - Thermal Design Power (TDP) power setting (watts)

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify powerstat_package_thermal_design_power_watts metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_telegraf_running()

    get_logger().log_test_case_step("Verify powerstat_package_thermal_design_power_watts metric is present on all nodes")
    power_metrics.validate_metrics(["powerstat_package_thermal_design_power_watts"], "should be present")


# ============================================================================
# Power Metrics - cAdvisor container perf events total
# ============================================================================


def test_metric_container_perf_events_total(request: FixtureRequest) -> None:
    """
    Power Metrics - cAdvisor container perf events total

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify container_perf_events_total metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_cadvisor_running()

    get_logger().log_test_case_step("Verify container_perf_events_total metric is present on all nodes")
    power_metrics.validate_metrics(["container_perf_events_total"], "should be present", endpoint=CADVISOR_METRICS_ENDPOINT, grep_pattern="container_perf_events_total", max_lines=50)


# ============================================================================
# Power Metrics - cAdvisor container perf events scaling ratio
# ============================================================================


def test_metric_container_perf_events_scaling_ratio(request: FixtureRequest) -> None:
    """
    Power Metrics - cAdvisor container perf events scaling ratio

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify container_perf_events_scaling_ratio metric is present on all nodes
    """
    setup_power_metrics(request)
    power_metrics = PowerMetricsKeywords(LabConnectionKeywords().get_active_controller_ssh())

    get_logger().log_test_case_step("Check if power-metrics is installed and pods are running")
    power_metrics.wait_for_cadvisor_running()

    get_logger().log_test_case_step("Verify container_perf_events_scaling_ratio metric is present on all nodes")
    power_metrics.validate_metrics(["container_perf_events_scaling_ratio"], "should be present", endpoint=CADVISOR_METRICS_ENDPOINT, grep_pattern="container_perf_events_scaling_ratio", max_lines=50)
