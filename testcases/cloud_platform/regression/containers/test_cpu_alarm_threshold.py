from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from framework.web.webdriver_core import WebDriverCore
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.platform_cpu.platform_cpu_stress_keywords import CPU_ALARM_ID, PlatformCpuStressKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from web_pages.horizon.admin.platform.horizon_fault_management_page import HorizonFaultManagementPage
from web_pages.horizon.login.horizon_login_page import HorizonLoginPage

# Overall wait budget (seconds) for the alarm to appear/clear. The 100.101
# alarm is slow to surface because the collectd/FM pipeline runs on the same
# saturated Platform cores, so it can exceed the default 600s.
CPU_ALARM_WAIT_TIMEOUT = 900


@mark.p2
def test_cpu_alarm_threshold(request: FixtureRequest):
    """Verify the Platform CPU alarm is raised and cleared under Platform CPU load.

    Test Steps:
        - Determine the active controller and its Platform CPU cores
        - Validate Platform CPU alarm (100.101) is not already present
        - Start one systemd stress service per Platform core
        - Verify that the Platform CPU threshold alarm (100.101) is raised
        - Stop the stress services to release CPU
        - Verify that the Platform CPU threshold alarm is cleared

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    stress_keywords = PlatformCpuStressKeywords(ssh_connection)
    alarm_keywords = AlarmListKeywords(ssh_connection)

    def cleanup():
        """Stop any Platform CPU stress services that may still be running."""
        get_logger().log_teardown_step("Stop Platform CPU stress services")
        stress_keywords.stop_platform_cpu_stress()

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Get Platform CPU cores for the active controller")
    hostname = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    platform_cores = SystemHostCPUKeywords(ssh_connection).get_platform_cores(hostname)
    get_logger().log_info(f"Host {hostname} Platform cores: {platform_cores}")
    validate_equals(
        len(platform_cores) > 0,
        True,
        f"Host {hostname} must have at least one Platform CPU core to stress",
    )

    get_logger().log_setup_step("Validate Platform CPU alarm is not present before applying stress")
    validate_equals(
        alarm_keywords.is_alarm_present(CPU_ALARM_ID),
        False,
        f"Platform CPU alarm {CPU_ALARM_ID} must not be present before stress is applied",
    )

    get_logger().log_test_case_step("Start Platform CPU stress on the Platform cores")
    stress_keywords.start_platform_cpu_stress(platform_cores)

    # Use wait_for_cpu_alarm (not AlarmListKeywords): each poll needs an extended
    # timeout since the FM CLI runs on the saturated Platform cores.
    get_logger().log_test_case_step("Wait for Platform CPU threshold alarm to appear")
    stress_keywords.wait_for_cpu_alarm(hostname, present=True, timeout=CPU_ALARM_WAIT_TIMEOUT)
    get_logger().log_info(f"Platform CPU alarm {CPU_ALARM_ID} was successfully raised")

    get_logger().log_test_case_step("Stop Platform CPU stress to release CPU pressure")
    stress_keywords.stop_platform_cpu_stress()

    get_logger().log_test_case_step("Wait for Platform CPU threshold alarm to clear")
    stress_keywords.wait_for_cpu_alarm(hostname, present=False, timeout=CPU_ALARM_WAIT_TIMEOUT)
    get_logger().log_info(f"Platform CPU alarm {CPU_ALARM_ID} was successfully cleared")


@mark.p2
def test_cpu_alarm_threshold_gui(request: FixtureRequest):
    """Verify the Platform CPU alarm appears and clears on the Horizon GUI Active Alarms page.

    Test Steps:
        - Login to Horizon as admin
        - Determine the active controller and its Platform CPU cores
        - Validate Platform CPU alarm (100.101) is not already present
        - Start one systemd stress service per Platform core
        - Navigate to Fault Management Active Alarms page and verify alarm (100.101) appears
        - Stop the stress services to release CPU
        - Verify the alarm disappears from the Active Alarms page

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    get_logger().log_setup_step("Establish SSH connection to the active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    stress_keywords = PlatformCpuStressKeywords(ssh_connection)
    alarm_keywords = AlarmListKeywords(ssh_connection)

    driver = WebDriverCore()

    def cleanup():
        """Stop any Platform CPU stress services and close the browser."""
        get_logger().log_teardown_step("Stop Platform CPU stress services")
        stress_keywords.stop_platform_cpu_stress()
        get_logger().log_teardown_step("Close browser")
        driver.quit()

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Open browser and log in to Horizon as admin")
    login_page = HorizonLoginPage(driver)
    login_page.navigate_to_login_page()
    login_page.login_as_admin()

    get_logger().log_setup_step("Get Platform CPU cores for the active controller")
    hostname = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    platform_cores = SystemHostCPUKeywords(ssh_connection).get_platform_cores(hostname)
    get_logger().log_info(f"Host {hostname} Platform cores: {platform_cores}")
    validate_equals(
        len(platform_cores) > 0,
        True,
        f"Host {hostname} must have at least one Platform CPU core to stress",
    )

    get_logger().log_setup_step("Validate Platform CPU alarm is not present before applying stress")
    validate_equals(
        alarm_keywords.is_alarm_present(CPU_ALARM_ID),
        False,
        f"Platform CPU alarm {CPU_ALARM_ID} must not be present before stress is applied",
    )

    get_logger().log_test_case_step("Start Platform CPU stress on the Platform cores")
    stress_keywords.start_platform_cpu_stress(platform_cores)

    # Longer timeout: with the cores saturated the collectd/FM pipeline feeding
    # Horizon lags, so the alarm can take well over the default 600s to appear.
    get_logger().log_test_case_step("Navigate to Active Alarms page and wait for Platform CPU alarm to appear")
    fault_management_page = HorizonFaultManagementPage(driver)
    fault_management_page.navigate_to_active_alarms_page()
    fault_management_page.wait_for_alarm_to_appear(CPU_ALARM_ID, timeout=CPU_ALARM_WAIT_TIMEOUT)
    get_logger().log_info(f"Platform CPU alarm {CPU_ALARM_ID} is visible on Horizon Active Alarms page")

    get_logger().log_test_case_step("Stop Platform CPU stress to release CPU pressure")
    stress_keywords.stop_platform_cpu_stress()

    get_logger().log_test_case_step("Wait for Platform CPU alarm to clear on Active Alarms page")
    fault_management_page.wait_for_alarm_to_clear(CPU_ALARM_ID, timeout=CPU_ALARM_WAIT_TIMEOUT)
    get_logger().log_info(f"Platform CPU alarm {CPU_ALARM_ID} cleared from Horizon Active Alarms page")
