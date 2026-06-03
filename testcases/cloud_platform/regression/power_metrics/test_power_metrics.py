from pytest import mark, FixtureRequest

from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from testcases.cloud_platform.regression.power_metrics.helper_power_metrics import HelperPowerMetrics

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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

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

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify all package metrics are collected")
    helper.assert_metrics_present_on_all_nodes(all_metrics, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value with only current_power_consumption via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that only current_power_consumption metric is shown")
        helper.assert_metrics_present_on_all_nodes(metrics_expected, "should still be present after filter")

        helper.logger.log_test_case_step("Verify that dram, tdp, cpu_base_frequency, uncore_frequency are NOT shown")
        helper.assert_metrics_absent_on_all_nodes(metrics_not_expected, "should NOT be present after filter override")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify all package metrics are collected again")
        helper.assert_metrics_present_on_all_nodes(all_metrics, "should be present again after restoring defaults")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    metrics_to_check = [
        "powerstat_package_current_power_consumption_watts",
        "powerstat_package_current_dram_power_consumption_watts",
        "powerstat_package_thermal_design_power_watts",
        "powerstat_package_cpu_base_frequency_mhz",
        "powerstat_package_uncore_frequency",
    ]

    override_files = ["empty_package_metrics_toml.yaml", "empty_package_metrics.yaml"]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify all package metrics are collected")
    helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value with empty package_metrics via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that NO package metrics are shown")
        helper.assert_metrics_absent_on_all_nodes(metrics_to_check, "should NOT be present with empty package_metrics override")
        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify all package metrics are collected again")
        helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present again after restoring defaults")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

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

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify all package metrics are collected")
    helper.assert_metrics_present_on_all_nodes(all_metrics, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that default package metrics are still shown")
        helper.assert_metrics_present_on_all_nodes(metrics_expected, "should still be present after without_package_metrics override")

        helper.logger.log_test_case_step("Verify that non default package metrics are not shown")
        helper.assert_metrics_absent_on_all_nodes(metrics_not_expected, "should NOT be present after filter override")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify all package metrics are collected again")
        helper.assert_metrics_present_on_all_nodes(all_metrics, "should be present again after restoring defaults")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

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

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify all per-CPU metrics are collected")
    helper.assert_metrics_present_on_all_nodes(all_metrics, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value with only cpu_frequency in cpu_metrics via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that only cpu_frequency metric is shown")
        helper.assert_metrics_present_on_all_nodes(metrics_expected, "should still be present after filter")

        helper.logger.log_test_case_step("Verify that busy_frequency, temperature, c0, c1, c6 are NOT shown")
        helper.assert_metrics_absent_on_all_nodes(metrics_not_expected, "should NOT be present after filter override")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify all per-CPU metrics are collected again")
        helper.assert_metrics_present_on_all_nodes(all_metrics, "should be present again after restoring defaults")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    metrics_to_check = [
        "powerstat_core_cpu_frequency_mhz",
        "powerstat_core_cpu_busy_frequency_mhz",
        "powerstat_core_cpu_temperature_celsius",
        "powerstat_core_cpu_c0_state_residency_percent",
        "powerstat_core_cpu_c1_state_residency_percent",
        "powerstat_core_cpu_c6_state_residency_percent",
    ]

    override_files = ["empty_cpu_metrics_toml.yaml", "empty_cpu_metrics.yaml"]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify all per-CPU metrics are collected")
    helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value with empty cpu_metrics via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that NO per-CPU metrics are shown")
        helper.assert_metrics_absent_on_all_nodes(metrics_to_check, "should NOT be present with empty cpu_metrics override")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify all per-CPU metrics are collected again")
        helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present again after restoring defaults")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    metrics_to_check = [
        "powerstat_core_cpu_frequency_mhz",
        "powerstat_core_cpu_busy_frequency_mhz",
        "powerstat_core_cpu_temperature_celsius",
        "powerstat_core_cpu_c0_state_residency_percent",
        "powerstat_core_cpu_c1_state_residency_percent",
        "powerstat_core_cpu_c6_state_residency_percent",
    ]

    override_files = ["without_cpu_metrics_toml.yaml", "without_cpu_metrics.yaml"]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify that per-CPU metrics are collected")
    helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that no per-CPU metrics are shown")
        helper.assert_metrics_absent_on_all_nodes(metrics_to_check, "should NOT be present with without_cpu_metrics override")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify that per-CPU metrics are collected again")
        helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present again after restoring defaults")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    included_cpu_ids = ["0", "1", "2", "3", "8"]
    excluded_cpu_ids = ["4", "5", "6", "7", "9"]
    all_cpu_ids = included_cpu_ids + excluded_cpu_ids
    override_files = ["filter_excluded_cpus_toml.yaml", "filter_excluded_cpus.yaml"]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
    helper.assert_cpu_ids_present_on_all_nodes(all_cpu_ids, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value with excluded_cpus via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that cpu_frequency is shown for kept CPUs")
        helper.assert_cpu_ids_present_on_all_nodes(included_cpu_ids, "should still be present after exclusion")

        helper.logger.log_test_case_step("Verify that cpu_frequency is NOT shown for excluded CPUs")
        helper.assert_cpu_ids_absent_on_all_nodes(excluded_cpu_ids, "should NOT be present after exclusion")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify that cpu_frequency is shown for all CPUs again")
        helper.assert_cpu_ids_present_on_all_nodes(all_cpu_ids, "should be present after restoring defaults")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    included_cpu_ids = ["0", "1", "2", "3", "5", "6", "8"]
    excluded_cpu_ids = ["4", "7", "9"]
    all_cpu_ids = included_cpu_ids + excluded_cpu_ids
    override_files = ["filter_included_cpus_toml.yaml", "filter_included_cpus.yaml"]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
    helper.assert_cpu_ids_present_on_all_nodes(all_cpu_ids, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value with included_cpus via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that cpu_frequency is shown for included CPUs")
        helper.assert_cpu_ids_present_on_all_nodes(included_cpu_ids, "should still be present after inclusion filter")

        helper.logger.log_test_case_step("Verify that cpu_frequency is NOT shown for excluded CPUs")
        helper.assert_cpu_ids_absent_on_all_nodes(excluded_cpu_ids, "should NOT be present after inclusion filter")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify that cpu_frequency is shown for all CPUs again")
        helper.assert_cpu_ids_present_on_all_nodes(all_cpu_ids, "should be present after restoring defaults")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    metrics_to_check = ["powerstat_core_cpu_frequency_mhz"]
    override_files = ["excluded_cpus_empty_toml.yaml", "excluded_cpus_empty.yaml"]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
    helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value with empty excluded_cpus via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that cpu_frequency remains shown for all CPUs (empty means no exclusion)")
        helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should remain present with empty excluded_cpus")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
        helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present after restore")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    metrics_to_check = ["powerstat_core_cpu_frequency_mhz"]
    override_files = ["included_cpus_empty_toml.yaml", "included_cpus_empty.yaml"]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
    helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present before override")
    for override_file in override_files:
        helper.logger.log_test_case_step(f"Update telegraf helm value with empty included_cpus via {override_file}")
        helper.upload_and_apply_helm_override(override_file)

        helper.logger.log_test_case_step("Reapply power-metrics application and wait")
        SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
        helper.wait_for_telegraf_running()

        helper.logger.log_test_case_step("Verify that cpu_frequency remains shown for all CPUs (empty means all included)")
        helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should remain present with empty included_cpus")

        helper.logger.log_test_case_step("Delete the user_overrides, reapply, and wait")
        helper.delete_override_and_reapply()

        helper.logger.log_test_case_step("Verify that cpu_frequency is shown for all CPUs")
        helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present after restore")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    metrics_to_check = [
        "powerstat_package_cpu_base_frequency_mhz",
        "powerstat_package_current_power_consumption_watts",
        "linux_cpu_cpuinfo_min_freq",
    ]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify metrics are being collected")
    helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present before disabling telegraf")

    helper.logger.log_test_case_step("Disable telegraf via telegraf_disabled.yaml override")
    helper.upload_and_apply_helm_override("telegraf_disabled.yaml")

    helper.logger.log_test_case_step("Reapply power-metrics application")
    SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)

    helper.logger.log_test_case_step("Verify that telegraf pod is NOT running")
    helper.assert_telegraf_not_running()

    helper.logger.log_test_case_step("Verify that no telegraf metrics are shown")
    helper.assert_metrics_absent_on_all_nodes(metrics_to_check, "should NOT be present after disabling telegraf")

    helper.logger.log_test_case_step("Enable telegraf via telegraf_enabled.yaml override")
    helper.upload_and_apply_helm_override("telegraf_enabled.yaml")

    helper.logger.log_test_case_step("Reapply power-metrics application and wait")
    SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify that metrics are shown once again")
    helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present again after re-enabling telegraf")


# ============================================================================
# Power Metrics - Change Helm values - Disable and Enable cAdvisor
# ============================================================================


def test_change_helm_values_disable_and_enable_cadvisor(request: FixtureRequest) -> None:
    """
    Power Metrics - Change Helm values - Disable and Enable cAdvisor perf events

    Test Steps:
        1. Check if power-metrics is installed and pods are running
        2. Verify cAdvisor perf metrics are being collected
        3. Disable perf_events via cadvisor_disabled.yaml override
        4. Reapply power-metrics application and wait
        5. Verify that no cAdvisor perf metrics are shown
        6. Enable perf_events via cadvisor_enabled.yaml override
        7. Reapply power-metrics application and wait
        8. Verify that cAdvisor perf metrics are shown once again
    """
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    cadvisor_endpoint = "cadvisor.power-metrics.svc.cluster.local/metrics"

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_cadvisor_running()

    helper.logger.log_test_case_step("Verify cAdvisor perf metrics are being collected")
    helper.assert_metrics_present_on_all_nodes(["container_perf_events_total"], "should be present before disabling perf_events", cadvisor_endpoint, grep_pattern="container_perf_events_total", max_lines=50)
    helper.assert_metrics_present_on_all_nodes(["container_perf_events_scaling_ratio"], "should be present before disabling perf_events", cadvisor_endpoint, grep_pattern="container_perf_events_scaling_ratio", max_lines=50)

    helper.logger.log_test_case_step("Disable perf_events via cadvisor_disabled.yaml override")
    helper.upload_and_apply_helm_override("cadvisor_disabled.yaml", chart_name="cadvisor")

    helper.logger.log_test_case_step("Reapply power-metrics application and wait")
    SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
    helper.wait_for_cadvisor_running()

    helper.logger.log_test_case_step("Verify that no cAdvisor perf metrics are shown")
    helper.assert_metrics_absent_on_all_nodes(["container_perf_events_total"], "should NOT be present after disabling perf_events", cadvisor_endpoint, grep_pattern="container_perf_events_total", max_lines=50)
    helper.assert_metrics_absent_on_all_nodes(["container_perf_events_scaling_ratio"], "should NOT be present after disabling perf_events", cadvisor_endpoint, grep_pattern="container_perf_events_scaling_ratio", max_lines=50)

    helper.logger.log_test_case_step("Enable perf_events via cadvisor_enabled.yaml override")
    helper.upload_and_apply_helm_override("cadvisor_enabled.yaml", chart_name="cadvisor")

    helper.logger.log_test_case_step("Reapply power-metrics application and wait")
    SystemApplicationApplyKeywords(helper.ssh_connection).system_application_apply(helper.app_name)
    helper.wait_for_cadvisor_running()

    helper.logger.log_test_case_step("Verify that cAdvisor perf metrics are shown once again")
    helper.assert_metrics_present_on_all_nodes(["container_perf_events_total"], "should be present again after re-enabling perf_events", cadvisor_endpoint, grep_pattern="container_perf_events_total", max_lines=50)
    helper.assert_metrics_present_on_all_nodes(["container_perf_events_scaling_ratio"], "should be present again after re-enabling perf_events", cadvisor_endpoint, grep_pattern="container_perf_events_scaling_ratio", max_lines=50)


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_core_cpu_temperature_celsius metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_core_cpu_temperature_celsius"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_core_cpu_c6_state_residency_percent metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_core_cpu_c6_state_residency_percent"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_core_cpu_c1_state_residency_percent metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_core_cpu_c1_state_residency_percent"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_core_cpu_c0_state_residency_percent metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_core_cpu_c0_state_residency_percent"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_core_cpu_busy_frequency_mhz metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_core_cpu_busy_frequency_mhz"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify linux_cpu_scaling_cur_freq metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["linux_cpu_scaling_cur_freq"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify linux_cpu_cpuinfo_max_freq metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["linux_cpu_cpuinfo_max_freq"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify linux_cpu_cpuinfo_min_freq metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["linux_cpu_cpuinfo_min_freq"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    metrics_to_check = [
        "powerstat_package_uncore_frequency_mhz_cur",
        "powerstat_package_uncore_frequency_limit_mhz_max",
        "powerstat_package_uncore_frequency_limit_mhz_min",
    ]

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_package_uncore_frequency metrics are present on all nodes")
    helper.assert_metrics_present_on_all_nodes(metrics_to_check, "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_package_cpu_base_frequency_mhz metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_package_cpu_base_frequency_mhz"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_package_current_dram_power_consumption_watts metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_package_current_dram_power_consumption_watts"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_package_current_power_consumption_watts metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_package_current_power_consumption_watts"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_telegraf_running()

    helper.logger.log_test_case_step("Verify powerstat_package_thermal_design_power_watts metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["powerstat_package_thermal_design_power_watts"], "should be present")


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    cadvisor_endpoint = "cadvisor.power-metrics.svc.cluster.local/metrics"

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_cadvisor_running()

    helper.logger.log_test_case_step("Verify container_perf_events_total metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["container_perf_events_total"], "should be present", cadvisor_endpoint, grep_pattern="container_perf_events_total", max_lines=50)


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
    helper = HelperPowerMetrics()
    helper.setup_method()
    request.addfinalizer(helper.teardown_method)

    cadvisor_endpoint = "cadvisor.power-metrics.svc.cluster.local/metrics"

    helper.logger.log_test_case_step("Check if power-metrics is installed and pods are running")
    helper.wait_for_cadvisor_running()

    helper.logger.log_test_case_step("Verify container_perf_events_scaling_ratio metric is present on all nodes")
    helper.assert_metrics_present_on_all_nodes(["container_perf_events_scaling_ratio"], "should be present", cadvisor_endpoint, grep_pattern="container_perf_events_scaling_ratio", max_lines=50)
