from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.ptp.gnss_monitoring_keywords import GnssMonitoringKeywords
from keywords.cloud_platform.system.ptp.ptp_readiness_keywords import PTPReadinessKeywords
from keywords.cloud_platform.system.ptp.ptp_setup_executor_keywords import PTPSetupExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_teardown_executor_keywords import PTPTeardownExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_verify_config_keywords import PTPVerifyConfigKeywords
from keywords.cloud_platform.system.ptp.system_host_ptp_instance_keywords import SystemHostPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_keywords import SystemPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_parameter_keywords import SystemPTPInstanceParameterKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords


@mark.p0
@mark.lab_has_gnr_d
def test_delete_and_add_all_ptp_configuration() -> None:
    """This test verifies that all PTP configurations can be cleanly removed
    and re-added, ensuring proper system state management.

    Test Steps:
        1. Delete all existing PTP configurations
        2. Add all PTP configurations from template
        3. Verify all PTP configurations are properly applied
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    get_logger().log_info("Delete all PTP configuration")
    ptp_teardown_keywords = PTPTeardownExecutorKeywords(ssh_connection)
    ptp_teardown_keywords.delete_all_ptp_configurations()

    get_logger().log_info("Add all PTP configuration")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/ptp_data_gnr_d_sx_gnss_monitoring.json5")
    ptp_setup_executor_keywords = PTPSetupExecutorKeywords(ssh_connection, ptp_setup_template_path)
    ptp_setup_executor_keywords.add_all_ptp_configurations()

    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-0"))
    ptp_readiness_keywords.wait_for_port_state_appear_in_port_data_set("ptp-inst1", ["MASTER"])
    ptp_readiness_keywords.wait_for_gm_clock_class_appear_in_parent_data_set("ptp-inst1", [6, 7])

    get_logger().log_info("Verify all PTP configuration")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()


@mark.p0
@mark.lab_has_gnr_d
def test_gnss_environment_setup_verification(request) -> None:
    """Verify test environment setup and GNSS device availability for monitoring functionality.

    This test ensures that all required GNSS hardware and software components
    are properly configured and operational before running monitoring tests.

    Args:
        request (pytest.FixtureRequest): Pytest request fixture for test cleanup registration.

    Test Steps:
        1. Check GNSS device availability at /dev/ttyACM0
        2. Verify GNSS data stream contains NMEA sentences
        3. Check zl3073x kernel module is loaded
        4. Verify network interface is UP with IP address
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    get_logger().log_test_case_step("Checking GNSS device availability")
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)
    gnss_monitoring_keywords.verify_device_exists("/dev/ttyACM0")

    get_logger().log_test_case_step("Verifying GNSS data stream")
    gnss_data = ssh_connection.send_as_sudo("timeout 5 cat /dev/ttyACM0 | head -10")
    validate_str_contains(gnss_data, "$GN", "Should receive NMEA sentences")

    get_logger().log_test_case_step("Checking zl3073x module")
    module_check = ssh_connection.send("lsmod | grep zl3073x")
    validate_str_contains(module_check, "zl3073x", "zl3073x module should be loaded")

    get_logger().log_test_case_step("Verifying network interface")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/ptp_data_gnr_d_sx_gnss_monitoring.json5")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)

    interfaces = ptp_setup.get_ptp4l_setup("ptp1").get_ptp_interface("ptp1if1").get_interfaces_for_hostname("controller-0")
    if not interfaces:
        raise Exception("No interfaces found for controller-0 NIC1")
    ctrl0_nic1_interface = interfaces[0]

    interface_check = ssh_connection.send(f"ip a sh {ctrl0_nic1_interface}")
    validate_str_contains(interface_check, "UP", "Interface should be UP")
    validate_str_contains(interface_check, "inet", "Interface should have IP address")


@mark.p0
@mark.lab_has_gnr_d
def test_gnss_monitoring_basic_instance_creation(request) -> None:
    """Verify GNSS monitoring instance can be created and configured with proper service activation.

    This test validates the complete lifecycle of creating a GNSS monitoring
    instance, configuring parameters, and verifying proper operation including
    service activation and alarm generation.

    Args:
        request (pytest.FixtureRequest): Pytest request fixture for test cleanup registration.

    Test Steps:
        1. Create and configure GNSS monitoring instance
        2. Apply configuration and verify services
        3. Verify PTY devices and data flow
        4. Check metrics and alarm conditions
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)
    ptp_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)
    host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    alarm_keywords = AlarmListKeywords(ssh_connection)

    def cleanup_monitoring_instance():
        """Clean up GNSS monitoring instance."""
        get_logger().log_teardown_step("Cleaning up GNSS monitoring instance")
        host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error("controller-0", "test-monitor")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "satellite_count=150")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "signal_quality_db=300")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'devices="/dev/ttyACM0 /dev/gnssx"')
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'cmdline_opts="-D 7"')
        ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    request.addfinalizer(cleanup_monitoring_instance)

    get_logger().log_test_case_step("Creating GNSS monitor instance")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor")

    get_logger().log_test_case_step("Configuring monitoring parameters")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=150")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=300")

    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'devices="/dev/ttyACM0 /dev/gnssx"')
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'cmdline_opts="-D 7"')

    get_logger().log_test_case_step("Assigning to host")
    host_ptp_instance_keywords.system_host_ptp_instance_assign("controller-0", "test-monitor")

    get_logger().log_test_case_step("Applying configuration")
    ptp_instance_keywords.system_ptp_instance_apply()

    get_logger().log_test_case_step("Waiting for services to be ready")
    gnss_monitoring_keywords.wait_for_monitoring_services_active(devices=["/dev/ttyACM0", "/dev/gnssx"])

    get_logger().log_test_case_step("Verifying GNSS monitor configuration file")
    gnss_monitoring_keywords.verify_monitoring_configuration_file(150, 300, "/dev/ttyACM0 /dev/gnssx")

    get_logger().log_test_case_step("Verify ts2phc configuration for nmea_serialport")
    gnss_monitoring_keywords.verify_ts2phc_config_serialport("ts1", "/dev/ttyACM0.pty")

    get_logger().log_test_case_step("Verifying PTY devices created")
    gnss_monitoring_keywords.verify_pty_device_exists("/dev/ttyACM0", True)
    gnss_monitoring_keywords.verify_device_exists("/dev/ttyACM0.pty")

    get_logger().log_test_case_step("Testing GNSS data through PTY")
    gnss_monitoring_keywords.verify_gnss_pty_data("/dev/ttyACM0")

    get_logger().log_test_case_step("Checking current satellite count and signal quality for /dev/ttyACM0")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/ttyACM0")
    get_satellite_count_ttyACM0 = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_satellite_count()
    get_signal_quality_max_ttyACM0 = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS satellite count for /dev/ttyACM0: {get_satellite_count_ttyACM0}")
    get_logger().log_info(f"Current GNSS signal quality for /dev/ttyACM0: {get_signal_quality_max_ttyACM0}")

    get_logger().log_test_case_step("Checking current satellite count and signal quality for /dev/gnssx")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/gnssx")
    get_satellite_count_gnssx = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/gnssx").get_satellite_count()
    get_signal_quality_max_gnssx = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/gnssx").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS satellite count for /dev/gnssx: {get_satellite_count_gnssx}")
    get_logger().log_info(f"Current GNSS signal quality for /dev/gnssx: {get_signal_quality_max_gnssx}")

    get_logger().log_test_case_step("Verifying alarm conditions")
    expected_alarms = []

    # Check conditions and add expected alarms with dynamic values
    get_logger().log_info(f"gnssx satellite count {get_satellite_count_gnssx} < 150, expecting satellite alarm")
    satellite_alarm_gnssx = AlarmListObject()
    satellite_alarm_gnssx.set_alarm_id("100.119")
    satellite_alarm_gnssx.set_reason_text(f"controller-0 GNSS satellite count below threshold state: satellite count {get_satellite_count_gnssx} \(expected: >= 150\)")
    satellite_alarm_gnssx.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/gnssx.ptp=GNSS-satellite-count")
    expected_alarms.append(satellite_alarm_gnssx)

    get_logger().log_info(f"gnssx signal quality {get_signal_quality_max_gnssx} < 300, expecting signal quality alarm")
    signal_quality_alarm_gnssx = AlarmListObject()
    signal_quality_alarm_gnssx.set_alarm_id("100.119")
    signal_quality_alarm_gnssx.set_reason_text(r"controller-0 GNSS signal quality db below threshold state: signal_quality_db [\d\.]+\s+\(expected: >= 300.0\)")
    signal_quality_alarm_gnssx.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/gnssx.ptp=GNSS-signal-quality-db")
    expected_alarms.append(signal_quality_alarm_gnssx)

    get_logger().log_info(f"ttyACM0 satellite count {get_satellite_count_ttyACM0} < 150, expecting satellite alarm")
    satellite_alarm_ttyACM0 = AlarmListObject()
    satellite_alarm_ttyACM0.set_alarm_id("100.119")
    satellite_alarm_ttyACM0.set_reason_text(f"controller-0 GNSS satellite count below threshold state: satellite count {get_satellite_count_ttyACM0} \(expected: >= 150\)")
    satellite_alarm_ttyACM0.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-satellite-count")
    expected_alarms.append(satellite_alarm_ttyACM0)

    get_logger().log_info(f"ttyACM0 signal quality {get_signal_quality_max_ttyACM0} < 300, expecting signal quality alarm")
    signal_quality_alarm_ttyACM0 = AlarmListObject()
    signal_quality_alarm_ttyACM0.set_alarm_id("100.119")
    signal_quality_alarm_ttyACM0.set_reason_text(r"controller-0 GNSS signal quality db below threshold state: signal_quality_db [\d\.]+\s+\(expected: >= 300.0\)")
    signal_quality_alarm_ttyACM0.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-signal-quality-db")
    expected_alarms.append(signal_quality_alarm_ttyACM0)

    # Always expect signal loss alarm for gnssx
    signal_loss_alarm = AlarmListObject()
    signal_loss_alarm.set_alarm_id("100.119")
    signal_loss_alarm.set_reason_text("controller-0 GNSS signal loss state: signal lock False \(expected: True\)")
    signal_loss_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/gnssx.ptp=GNSS-signal-loss")
    expected_alarms.append(signal_loss_alarm)

    get_logger().log_info(f"Expecting {len(expected_alarms)} alarms based on current conditions")

    # Wait for expected alarms to appear
    alarm_keywords.set_timeout_in_seconds(180)
    alarm_keywords.wait_for_alarms_to_appear(expected_alarms)
    get_logger().log_info("All expected alarms appeared successfully")

    get_logger().log_test_case_step("Validate that only expected alarms are present")
    all_alarms = alarm_keywords.alarm_list()
    gnss_alarms = [alarm for alarm in all_alarms if "100.119" in alarm.get_alarm_id()]
    validate_equals(len(gnss_alarms), len(expected_alarms), "Number of GNSS alarms should match expected count")


@mark.p0
@mark.lab_has_gnr_d
def test_gnss_monitoring_satellite_count_alarm(request) -> None:
    """Test GNSS monitoring satellite count alarm generation and clearing.

    This test verifies that satellite count alarms are properly raised when
    the threshold is set above current satellite count and cleared when
    the threshold is lowered below current count.

    Args:
        request (pytest.FixtureRequest): Pytest request fixture for test cleanup.

    Test Steps:
        1. Create monitoring instance with high satellite threshold
        2. Wait for satellite count alarm to appear
        3. Lower threshold and verify alarm clears
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    ptp_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)
    host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)

    get_logger().log_setup_step("Creating monitoring instance with high satellite threshold")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=15")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'devices="/dev/ttyACM0"')
    host_ptp_instance_keywords.system_host_ptp_instance_assign("controller-0", "test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_setup_step("Get current satellite count for /dev/ttyACM0 device")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/ttyACM0")
    get_satellite_count = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_satellite_count()
    get_logger().log_info(f"Current GNSS satellite count for /dev/ttyACM0 device: {get_satellite_count}")

    # Increasing satellite count to trigger alarm - ensure it's always higher than current
    if get_satellite_count > 15:
        satellite_count = get_satellite_count + 15
        ptp_parameter_keywords.system_ptp_instance_parameter_delete("test-monitor", "satellite_count=15")
        ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", f"satellite_count={satellite_count}")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])
    else:
        satellite_count = get_satellite_count

    # Calculate lowering satellite threshold to clear alarm - must be less than current count
    lowering_satellite_count = max(0, get_satellite_count // 2)
    get_logger().log_info(f"Will lower satellite threshold to {lowering_satellite_count} to clear alarm")

    def cleanup_monitoring_instance():
        """Clean up GNSS monitoring instance."""
        get_logger().log_teardown_step("Cleaning up GNSS monitoring instance")
        host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error("controller-0", "test-monitor")
        if lowering_satellite_count is not None:
            ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", f"satellite_count={lowering_satellite_count}")
        else:
            ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", f"satellite_count={satellite_count}")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "signal_quality_db=30")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'devices="/dev/ttyACM0"')
        ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    request.addfinalizer(cleanup_monitoring_instance)

    get_logger().log_test_case_step("Waiting for satellite count alarm to appear")
    satellite_alarm = AlarmListObject()
    satellite_alarm.set_alarm_id("100.119")
    satellite_alarm.set_reason_text(f"controller-0 GNSS satellite count below threshold state: satellite count {get_satellite_count} \(expected: >= {satellite_count}\)")
    satellite_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-satellite-count")

    alarm_keywords = AlarmListKeywords(ssh_connection)
    alarm_keywords.set_timeout_in_seconds(240)
    alarm_keywords.wait_for_alarms_to_appear([satellite_alarm])

    get_logger().log_test_case_step("Lowering satellite threshold to clear alarm")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete("test-monitor", f"satellite_count={satellite_count}")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", f"satellite_count={lowering_satellite_count}")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_test_case_step("Waiting for alarm to clear")
    lowering_satellite_alarm = AlarmListObject()
    lowering_satellite_alarm.set_alarm_id("100.119")
    lowering_satellite_alarm.set_reason_text(f"controller-0 GNSS satellite count below threshold state: satellite count {get_satellite_count} \(expected: >= {lowering_satellite_count}\)")
    lowering_satellite_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-satellite-count")
    alarm_keywords.set_timeout_in_seconds(240)
    alarm_keywords.wait_for_alarms_cleared([satellite_alarm, lowering_satellite_alarm])


@mark.p0
@mark.lab_has_gnr_d
def test_gnss_monitoring_signal_quality_alarm(request) -> None:
    """Test GNSS monitoring signal quality alarm generation and clearing.

    This test verifies that signal quality alarms are properly raised when
    the threshold is set above current signal quality and cleared when
    the threshold is lowered below current quality.

    Args:
        request (pytest.FixtureRequest): Pytest request fixture for test cleanup registration.

    Test Steps:
        1. Create monitoring instance with high signal quality threshold
        2. Wait for signal quality alarm to appear
        3. Lower threshold and verify alarm clears
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    ptp_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)
    host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)

    get_logger().log_setup_step("Creating monitoring instance with high signal quality threshold")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'devices="/dev/ttyACM0"')
    host_ptp_instance_keywords.system_host_ptp_instance_assign("controller-0", "test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_setup_step("Get current GNSS signal quality for /dev/ttyACM0 device")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/ttyACM0")
    get_signal_quality_max = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS signal quality for /dev/ttyACM0 device: {get_signal_quality_max}")

    # Increasing signal quality db to trigger alarm - ensure it's always higher than current
    if get_signal_quality_max > 30:
        signal_quality_db = get_signal_quality_max + 30
        ptp_parameter_keywords.system_ptp_instance_parameter_delete("test-monitor", "signal_quality_db=30")
        ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", f"signal_quality_db={signal_quality_db}")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])
    else:
        signal_quality_db = get_signal_quality_max

    # Calculate lowering signal quality db threshold to clear alarm - must be less than current count
    lowering_signal_quality_db = max(0, get_signal_quality_max // 2)
    get_logger().log_info(f"Will lower signal quality db threshold to {lowering_signal_quality_db} to clear alarm")

    def cleanup_monitoring_instance():
        """Clean up GNSS monitoring instance."""
        get_logger().log_teardown_step("Cleaning up GNSS monitoring instance")
        host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error("controller-0", "test-monitor")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "satellite_count=8")
        if lowering_signal_quality_db is not None:
            ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", f"signal_quality_db={lowering_signal_quality_db}")
        else:
            ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", f"signal_quality_db={signal_quality_db}")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'devices="/dev/ttyACM0"')
        ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    request.addfinalizer(cleanup_monitoring_instance)

    get_logger().log_test_case_step("Waiting for signal quality alarm to appear")
    signal_quality_alarm = AlarmListObject()
    signal_quality_alarm.set_alarm_id("100.119")
    signal_quality_alarm.set_reason_text(r"controller-0 GNSS signal quality db below threshold state: signal_quality_db [\d\.]+\s+\(expected: >= [\d\.]+\)")
    signal_quality_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-signal-quality-db")

    alarm_keywords = AlarmListKeywords(ssh_connection)
    alarm_keywords.set_timeout_in_seconds(240)
    alarm_keywords.wait_for_alarms_to_appear([signal_quality_alarm])

    get_logger().log_test_case_step("Lowering signal quality threshold to clear alarm")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete("test-monitor", f"signal_quality_db={signal_quality_db}")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", f"signal_quality_db={lowering_signal_quality_db}")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_test_case_step("Waiting for alarm to clear")
    alarm_keywords.set_timeout_in_seconds(240)
    alarm_keywords.wait_for_alarms_cleared([signal_quality_alarm])


@mark.p1
@mark.lab_has_gnr_d
def test_gnss_monitoring_parameter_updates(request) -> None:
    """Test dynamic parameter updates and reconfiguration of GNSS monitoring.

    This test verifies that monitoring parameters can be updated dynamically
    and that the changes are properly applied to the running configuration.

    Args:
        request (pytest.FixtureRequest): Pytest request fixture for test cleanup registration.

    Test Steps:
        1. Create monitoring instance with initial parameters
        2. Update parameters to new values
        3. Verify updated configuration and alarm conditions
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)
    ptp_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)
    host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    alarm_keywords = AlarmListKeywords(ssh_connection)

    def cleanup_monitoring_instance():
        """Clean up GNSS monitoring instance."""
        get_logger().log_teardown_step("Cleaning up GNSS monitoring instance")
        host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error("controller-0", "test-monitor")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "satellite_count=150")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "signal_quality_db=300")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'devices="/dev/ttyACM0"')
        ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    request.addfinalizer(cleanup_monitoring_instance)

    get_logger().log_setup_step("Creating monitoring instance with initial parameters")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'devices="/dev/ttyACM0"')
    host_ptp_instance_keywords.system_host_ptp_instance_assign("controller-0", "test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_setup_step("Verifying initial configuration")
    gnss_monitoring_keywords.verify_monitoring_configuration_file(8, 30, "/dev/ttyACM0")

    get_logger().log_test_case_step("Updating ptp instance parameters")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete("test-monitor", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=150")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=300")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_test_case_step("Waiting for updated configuration")
    gnss_monitoring_keywords.wait_for_monitoring_configuration_file(150, 300, "/dev/ttyACM0")

    get_logger().log_test_case_step("Testing GNSS data through PTY")
    gnss_monitoring_keywords.verify_gnss_pty_data("/dev/ttyACM0")

    get_logger().log_test_case_step("Get current satellite count and signal quality for /dev/ttyACM0")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/ttyACM0")
    get_satellite_count = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_satellite_count()
    get_signal_quality_max = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS satellite count for /dev/ttyACM0: {get_satellite_count}")
    get_logger().log_info(f"Current GNSS signal quality for /dev/ttyACM0: {get_signal_quality_max}")

    get_logger().log_test_case_step("Verifying alarm conditions")
    expected_alarms = []
    get_logger().log_info(f"ttyACM0 satellite count {get_satellite_count} < 150, expecting satellite alarm")
    satellite_alarm = AlarmListObject()
    satellite_alarm.set_alarm_id("100.119")
    satellite_alarm.set_reason_text(f"controller-0 GNSS satellite count below threshold state: satellite count {get_satellite_count} \(expected: >= 150\)")
    satellite_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-satellite-count")
    expected_alarms.append(satellite_alarm)

    get_logger().log_info(f"ttyACM0 signal quality {get_signal_quality_max} < 300, expecting signal quality alarm")
    signal_quality_alarm = AlarmListObject()
    signal_quality_alarm.set_alarm_id("100.119")
    signal_quality_alarm.set_reason_text(r"controller-0 GNSS signal quality db below threshold state: signal_quality_db [\d\.]+\s+\(expected: >= [\d\.]+\)")
    signal_quality_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-signal-quality-db")
    expected_alarms.append(signal_quality_alarm)

    # Wait for expected alarms to appear
    alarm_keywords.set_timeout_in_seconds(240)
    alarm_keywords.wait_for_alarms_to_appear(expected_alarms)
    get_logger().log_info("All expected alarms appeared successfully")

    # Validate that only expected alarms are present
    all_alarms = alarm_keywords.alarm_list()
    gnss_alarms = [alarm for alarm in all_alarms if "100.119" in alarm.get_alarm_id()]
    validate_equals(len(gnss_alarms), len(expected_alarms), "Number of GNSS alarms should match expected count")


@mark.p1
@mark.lab_has_gnr_d
def test_gnss_monitoring_persistence_after_reboot(request) -> None:
    """Test GNSS monitoring persistence after host operations.

    This test verifies that GNSS monitoring configuration and functionality
    persist through host lock/unlock operations and system reboots.

    Args:
        request (pytest.FixtureRequest): Pytest request fixture for test cleanup registration.

    Test Steps:
        1. Create and configure GNSS monitoring instance
        2. Perform host lock/unlock operations
        3. Perform system reboot
        4. Verify monitoring persists after operations
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)
    ptp_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)
    host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    alarm_keywords = AlarmListKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)

    def cleanup_monitoring_instance():
        """Clean up GNSS monitoring instance."""
        get_logger().log_teardown_step("Cleaning up GNSS monitoring instance")
        host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error("controller-0", "test-monitor")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "satellite_count=300")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "signal_quality_db=600")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'devices="/dev/ttyACM0"')
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'cmdline_opts="-D 7"')
        ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    request.addfinalizer(cleanup_monitoring_instance)

    get_logger().log_setup_step("Creating monitoring instance")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=300")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=600")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'devices="/dev/ttyACM0"')
    host_ptp_instance_keywords.system_host_ptp_instance_assign("controller-0", "test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_setup_step("Verifying GNSS monitor configuration file")
    gnss_monitoring_keywords.verify_monitoring_configuration_file(300, 600, "/dev/ttyACM0")

    get_logger().log_test_case_step("Verifying PTY devices created")
    gnss_monitoring_keywords.verify_pty_device_exists("/dev/ttyACM0", True)

    get_logger().log_setup_step("Testing GNSS data through PTY")
    gnss_monitoring_keywords.verify_gnss_pty_data("/dev/ttyACM0")

    get_logger().log_setup_step("Checking current satellite count and signal quality for /dev/ttyACM0")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/ttyACM0")
    get_satellite_count = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_satellite_count()
    get_signal_quality_max = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS satellite count for /dev/ttyACM0: {get_satellite_count}")
    get_logger().log_info(f"Current GNSS signal quality for /dev/ttyACM0: {get_signal_quality_max}")

    get_logger().log_setup_step("Checking for expected alarms")
    expected_alarms = []
    get_logger().log_info(f"satellite count {get_satellite_count} < 300, expecting satellite alarm")
    satellite_alarm = AlarmListObject()
    satellite_alarm.set_alarm_id("100.119")
    satellite_alarm.set_reason_text(r"controller-0 GNSS satellite count below threshold state: satellite count [\d]+\s+\(expected: >= 300\)")
    satellite_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-satellite-count")
    expected_alarms.append(satellite_alarm)

    get_logger().log_info(f"ttyACM0 signal quality {get_signal_quality_max} < 600, expecting signal quality alarm")
    signal_quality_alarm = AlarmListObject()
    signal_quality_alarm.set_alarm_id("100.119")
    signal_quality_alarm.set_reason_text(r"controller-0 GNSS signal quality db below threshold state: signal_quality_db [\d\.]+\s+\(expected: >= [\d\.]+\)")
    signal_quality_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-signal-quality-db")
    expected_alarms.append(signal_quality_alarm)

    # Wait for expected alarms to appear
    alarm_keywords.set_timeout_in_seconds(180)
    alarm_keywords.wait_for_alarms_to_appear(expected_alarms)
    get_logger().log_info("All expected alarms appeared successfully")

    get_logger().log_test_case_step("Lock and unlock host")
    lock_keywords = SystemHostLockKeywords(ssh_connection)
    lock_success = lock_keywords.lock_host("controller-0")
    validate_equals(lock_success, True, "Controller should lock successfully")

    unlock_success = lock_keywords.unlock_host("controller-0")
    validate_equals(unlock_success, True, "Controller should unlock successfully")

    get_logger().log_test_case_step("Verifying monitoring instance persists after lock and unlock")
    get_host_ptp_instance_for_name = host_ptp_instance_keywords.get_system_host_ptp_instance_list("controller-0").get_host_ptp_instance_for_name("test-monitor")
    validate_equals(get_host_ptp_instance_for_name.get_name(), "test-monitor", "Monitoring instance should persist after lock and unlock")

    get_logger().log_test_case_step("Verifying GNSS monitor configuration file after lock and unlock")
    config_exists = file_keywords.file_exists("/etc/linuxptp/ptpinstance/gnss-monitor-ptp.conf")
    validate_equals(config_exists, True, "Configuration file should exist")
    gnss_monitoring_keywords.verify_monitoring_configuration_file(300, 600, "/dev/ttyACM0")

    get_logger().log_test_case_step("Checking system services after lock and unlock")
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_test_case_step("Verifying PTY devices created")
    gnss_monitoring_keywords.verify_pty_device_exists("/dev/ttyACM0", True)

    get_logger().log_test_case_step("Testing GNSS data through PTY after lock and unlock")
    gnss_monitoring_keywords.verify_gnss_pty_data("/dev/ttyACM0")

    get_logger().log_test_case_step("Checking current satellite count and signal quality for /dev/ttyACM0 after lock and unlock")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/ttyACM0")
    get_satellite_count = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_satellite_count()
    get_signal_quality_max = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS satellite count for /dev/ttyACM0 : {get_satellite_count}")
    get_logger().log_info(f"Current GNSS signal quality for /dev/ttyACM0 : {get_signal_quality_max}")

    get_logger().log_test_case_step("Checking for expected alarms after lock and unlock")
    alarm_keywords.wait_for_alarms_to_appear(expected_alarms)
    get_logger().log_info("All expected alarms appeared successfully")

    # Validate that only expected alarms are present
    all_alarms = alarm_keywords.alarm_list()
    gnss_alarms = [alarm for alarm in all_alarms if "100.119" in alarm.get_alarm_id()]
    validate_equals(len(gnss_alarms), len(expected_alarms), "Number of GNSS alarms should match expected count")

    get_logger().log_test_case_step("Reboot host")
    # force reboot the active controller
    # get the prev uptime of the host so we can be sure it re-started
    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime("controller-0")
    ssh_connection.send_as_sudo("sudo reboot -f")
    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot("controller-0", pre_uptime_of_host)
    validate_equals(reboot_success, True, "Controller should reboot successfully")

    get_logger().log_test_case_step("Verifying monitoring instance persists after reboot")
    get_host_ptp_instance_for_name = host_ptp_instance_keywords.get_system_host_ptp_instance_list("controller-0").get_host_ptp_instance_for_name("test-monitor")
    validate_equals(get_host_ptp_instance_for_name.get_name(), "test-monitor", "Monitoring instance should persist after reboot")

    get_logger().log_test_case_step("Verifying GNSS monitor configuration file after reboot")
    gnss_monitoring_keywords.verify_monitoring_configuration_file(300, 600, "/dev/ttyACM0")

    get_logger().log_test_case_step("Checking system services after reboot")
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    get_logger().log_test_case_step("Verifying PTY devices created")
    gnss_monitoring_keywords.verify_pty_device_exists("/dev/ttyACM0", True)

    get_logger().log_test_case_step("Testing GNSS data through PTY after reboot")
    gnss_monitoring_keywords.verify_gnss_pty_data("/dev/ttyACM0")

    get_logger().log_test_case_step("Checking current satellite count and signal quality for /dev/ttyACM0 after reboot")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/ttyACM0")
    get_satellite_count = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_satellite_count()
    get_signal_quality_max = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS satellite count for /dev/ttyACM0 : {get_satellite_count}")
    get_logger().log_info(f"Current GNSS signal quality for /dev/ttyACM0 : {get_signal_quality_max}")

    get_logger().log_test_case_step("Checking for expected alarms after reboot")
    # Wait for expected alarms to appear
    alarm_keywords.set_timeout_in_seconds(180)
    alarm_keywords.wait_for_alarms_to_appear(expected_alarms)
    get_logger().log_info("All expected alarms appeared successfully")

    # Validate that only expected alarms are present
    all_alarms = alarm_keywords.alarm_list()
    gnss_alarms = [alarm for alarm in all_alarms if "100.119" in alarm.get_alarm_id()]
    validate_equals(len(gnss_alarms), len(expected_alarms), "Number of GNSS alarms should match expected count")


@mark.p0
@mark.lab_has_gnr_d
def test_gnss_monitoring_instance_removal(request):
    """
    GNSS Monitoring Instance Removal

    Verify complete cleanup when removing GNSS monitoring instance.
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)
    ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    alarm_keywords = AlarmListKeywords(ssh_connection)

    get_logger().log_setup_step("Creating monitoring instance")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'devices="/dev/ttyACM0"')
    host_ptp_instance_keywords.system_host_ptp_instance_assign("controller-0", "test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0"])

    gnss_monitoring_keywords.verify_pty_device_exists("/dev/ttyACM0", True)

    get_logger().log_test_case_step("Removing instance from host")
    host_ptp_instance_keywords.system_host_ptp_instance_remove("controller-0", "test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    gnss_monitoring_keywords.verify_pty_device_exists("/dev/ttyACM0", False)

    get_logger().log_test_case_step("Waiting for alarm to clear")
    alarm_keywords.set_timeout_in_seconds(180)
    ptp_alarm = AlarmListObject()
    ptp_alarm.set_alarm_id("100.119")
    alarm_keywords.wait_for_alarms_cleared([ptp_alarm])

    get_logger().log_test_case_step("Cleaning up GNSS monitoring instance")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'devices="/dev/ttyACM0"')
    ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'cmdline_opts="-D 7"')
    ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    error_message = ptp_instance_keywords.get_system_ptp_instance_show_with_error("test-monitor")
    validate_str_contains(error_message, "PTP instance not found: test-monitor", "Error message for non-existent instance")

    get_logger().log_test_case_step("Waiting for alarm to clear")
    alarm_keywords.set_timeout_in_seconds(180)
    alarm_keywords.wait_for_alarms_cleared([ptp_alarm])

    get_logger().log_test_case_step("Verify PTY devices removed")
    gnss_monitoring_keywords.verify_pty_device_exists("/dev/ttyACM0", False)
    get_logger().log_info("PTY devices cleaned up")

    get_logger().log_test_case_step("Verify configuration file removed")
    config_file_check = ssh_connection.send("ls /etc/linuxptp/ptpinstance/gnss-monitor-ptp.conf 2>/dev/null || echo 'not found'")
    config_file_check_str = "\n".join(config_file_check) if isinstance(config_file_check, list) else config_file_check
    validate_str_contains(config_file_check_str, "not found", "Check: /etc/linuxptp/ptpinstance/gnss-monitor-ptp.conf does not exist")
    get_logger().log_info("Configuration files removed")

    get_logger().log_test_case_step("Verify ts2phc configuration reverted for nmea_serialport")
    gnss_monitoring_keywords.verify_ts2phc_config_serialport("ts1", "/dev/ttyACM0")


@mark.p1
@mark.lab_has_gnr_d
def test_gnss_monitoring_single_instance_per_host(request):
    """
    Verify that only one PTP instance is allowed per host and appropriate error handling when attempting to assign multiple instances

    Test steps:
    1) Ensure existing GNSS monitor instance is assigned
    2) Create a second PTP instance
    3) Attempt to assign second instance to same host - should fail
    4) Confirm only original instance remains active
    5) Clean up second instance
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    ptp_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)
    host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)

    def cleanup_monitoring_instances():
        """Clean up GNSS monitoring instances."""
        get_logger().log_test_case_step("Cleaning up second instance")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor-2", "satellite_count=8")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor-2", "signal_quality_db=30")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor-2", 'devices="/dev/ttyACM0 /dev/gnssx"')
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor-2", 'cmdline_opts="-D 7"')
        ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor-2")

        get_logger().log_teardown_step("Cleaning up GNSS monitoring instances")
        host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error("controller-0", "test-monitor")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "satellite_count=8")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", "signal_quality_db=30")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'devices="/dev/ttyACM0 /dev/gnssx"')
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'cmdline_opts="-D 7"')
        ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    request.addfinalizer(cleanup_monitoring_instances)

    get_logger().log_test_case_step("Creating first GNSS monitoring instance")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'devices="/dev/ttyACM0 /dev/gnssx"')
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'cmdline_opts="-D 7"')
    host_ptp_instance_keywords.system_host_ptp_instance_assign("controller-0", "test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0", "/dev/gnssx"])

    get_logger().log_test_case_step("Verifying first instance assigned successfully")
    get_host_ptp_instance_for_name = host_ptp_instance_keywords.get_system_host_ptp_instance_list("controller-0").get_host_ptp_instance_for_name("test-monitor")
    validate_equals(get_host_ptp_instance_for_name.get_name(), "test-monitor", "First instance should be assigned")

    get_logger().log_test_case_step("Creating second PTP instance")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor-2")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor-2", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor-2", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor-2", 'devices="/dev/ttyACM0 /dev/gnssx"')
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor-2", 'cmdline_opts="-D 7"')

    get_logger().log_test_case_step("Attempting to assign second instance to same host - should fail")
    error_message = host_ptp_instance_keywords.system_host_ptp_instance_assign_with_error("controller-0", "test-monitor-2")
    validate_str_contains(error_message, "gnss-monitor ptp instance already exists on host", "Should get error about existing gnss-monitor instance")

    get_logger().log_test_case_step("Confirming only original instance remains active")
    gnss_monitoring_instance = ptp_instance_keywords.get_system_ptp_instance_show("test-monitor")
    validate_equals(gnss_monitoring_instance.system_ptp_instance_object.get_name(), "test-monitor", "Original instance should remain")


@mark.p0
@mark.lab_has_gnr_d
def test_gnss_monitoring_threshold_alarm_verification(request):
    """
    Verify satellite count and signal quality thresholds trigger appropriate alarms when breached

    Test Steps:
        1) Check current GNSS device metrics
        2) Set thresholds above current values
        3) Apply updated configuration
        4) Verify updated configuration file
        5) Check for threshold alarms
        6) Verify only valid device PTY exists
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    ptp_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)
    host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    gnss_monitoring_keywords = GnssMonitoringKeywords(ssh_connection)
    alarm_keywords = AlarmListKeywords(ssh_connection)

    get_logger().log_setup_step("Creating GNSS monitor")
    gnss_monitoring_keywords.create_monitoring_instance("test-monitor")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'devices="/dev/ttyACM0 /dev/gnssx"')
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", 'cmdline_opts="-D 7"')
    host_ptp_instance_keywords.system_host_ptp_instance_assign("controller-0", "test-monitor")
    ptp_instance_keywords.system_ptp_instance_apply()
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0", "/dev/gnssx"])

    get_logger().log_setup_step("Checking current satellite count and signal quality for /dev/ttyACM0")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/ttyACM0")
    get_satellite_count_ttyACM0 = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_satellite_count()
    get_signal_quality_max_ttyACM0 = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/ttyACM0").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS satellite count for /dev/ttyACM0: {get_satellite_count_ttyACM0}")
    get_logger().log_info(f"Current GNSS signal quality for /dev/ttyACM0: {get_signal_quality_max_ttyACM0}")

    get_logger().log_setup_step("Checking current satellite count and signal quality for /dev/gnssx")
    get_gnss_monitoring_data = gnss_monitoring_keywords.get_gnss_monitoring_data("/dev/gnssx")
    get_satellite_count_gnssx = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/gnssx").get_satellite_count()
    get_signal_quality_max_gnssx = get_gnss_monitoring_data.get_monitoring_data_for_device("/dev/gnssx").get_signal_quality_max()
    get_logger().log_info(f"Current GNSS satellite count for /dev/gnssx: {get_satellite_count_gnssx}")
    get_logger().log_info(f"Current GNSS signal quality for /dev/gnssx: {get_signal_quality_max_gnssx}")

    # Set thresholds higher than both devices' current values
    satellite_count = max(get_satellite_count_gnssx + 30, get_satellite_count_ttyACM0 + 30)
    signal_quality_max = max(int(get_signal_quality_max_gnssx) + 50, int(get_signal_quality_max_ttyACM0) + 50)
    get_logger().log_info(f"Setting satellite_count threshold to: {satellite_count}")
    get_logger().log_info(f"Setting signal_quality_max threshold to: {signal_quality_max}")

    def cleanup_monitoring_instance():
        """Clean up GNSS monitoring instance."""
        get_logger().log_teardown_step("Cleaning up GNSS monitoring instance")
        host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error("controller-0", "test-monitor")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", f"satellite_count={satellite_count}")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", f"signal_quality_db={signal_quality_max}")
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'devices="/dev/ttyACM0 /dev/gnssx"')
        ptp_parameter_keywords.system_ptp_instance_parameter_delete_with_error("test-monitor", 'cmdline_opts="-D 7"')
        ptp_instance_keywords.system_ptp_instance_delete_with_error("test-monitor")
        ptp_instance_keywords.system_ptp_instance_apply()
        gnss_monitoring_keywords.wait_for_monitoring_services_inactive()

    request.addfinalizer(cleanup_monitoring_instance)

    get_logger().log_test_case_step("Set thresholds above current values")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete("test-monitor", "satellite_count=8")
    ptp_parameter_keywords.system_ptp_instance_parameter_delete("test-monitor", "signal_quality_db=30")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", f"satellite_count={satellite_count}")
    ptp_parameter_keywords.system_ptp_instance_parameter_add("test-monitor", f"signal_quality_db={signal_quality_max}")
    system_ptp_instance_apply_output = ptp_instance_keywords.system_ptp_instance_apply()
    validate_equals(system_ptp_instance_apply_output, "Applying the PTP Instance configuration", "apply PTP instance configuration")
    gnss_monitoring_keywords.wait_for_monitoring_services_active(["/dev/ttyACM0", "/dev/gnssx"])

    get_logger().log_test_case_step("Verify updated configuration file")
    gnss_monitoring_keywords.wait_for_monitoring_configuration_file(satellite_count, signal_quality_max, "/dev/ttyACM0 /dev/gnssx")

    get_logger().log_test_case_step("Verifying alarm conditions")
    signal_loss_alarm = AlarmListObject()
    signal_loss_alarm.set_alarm_id("100.119")
    signal_loss_alarm.set_reason_text("controller-0 GNSS signal loss state: signal lock False \(expected: True\)")
    signal_loss_alarm.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/gnssx.ptp=GNSS-signal-loss")

    satellite_alarm_gnssx = AlarmListObject()
    satellite_alarm_gnssx.set_alarm_id("100.119")
    satellite_alarm_gnssx.set_reason_text(r"controller-0 GNSS satellite count below threshold state: satellite count [\d]+\s+\(expected: >= [\d]+\)")
    satellite_alarm_gnssx.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/gnssx.ptp=GNSS-satellite-count")

    signal_quality_alarm_gnssx = AlarmListObject()
    signal_quality_alarm_gnssx.set_alarm_id("100.119")
    signal_quality_alarm_gnssx.set_reason_text(r"controller-0 GNSS signal quality db below threshold state: signal_quality_db [\d\.]+\s+\(expected: >= [\d\.]+\)")
    signal_quality_alarm_gnssx.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/gnssx.ptp=GNSS-signal-quality-db")

    satellite_alarm_ttyACM0 = AlarmListObject()
    satellite_alarm_ttyACM0.set_alarm_id("100.119")
    satellite_alarm_ttyACM0.set_reason_text(r"controller-0 GNSS satellite count below threshold state: satellite count [\d]+\s+\(expected: >= [\d]+\)")
    satellite_alarm_ttyACM0.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-satellite-count")

    signal_quality_alarm_ttyACM0 = AlarmListObject()
    signal_quality_alarm_ttyACM0.set_alarm_id("100.119")
    signal_quality_alarm_ttyACM0.set_reason_text(r"controller-0 GNSS signal quality db below threshold state: signal_quality_db [\d\.]+\s+\(expected: >= [\d\.]+\)")
    signal_quality_alarm_ttyACM0.set_entity_id("host=controller-0.gnss-monitor=gnss-monitor-ptp.device_path=/dev/ttyACM0.ptp=GNSS-signal-quality-db")

    alarm_keywords.set_timeout_in_seconds(180)
    alarm_keywords.wait_for_alarms_to_appear([signal_loss_alarm, satellite_alarm_gnssx, signal_quality_alarm_gnssx, satellite_alarm_ttyACM0, signal_quality_alarm_ttyACM0])
    get_logger().log_info("All expected alarms appeared successfully")

    get_logger().log_test_case_step("Verify only valid device PTY exists")
    gnss_monitoring_keywords.verify_device_exists("/dev/ttyACM0.pty")
    gnss_monitoring_keywords.verify_device_exists("/dev/gnssx.pty")

    get_logger().log_test_case_step("Verify GNSS data through PTY")
    gnss_monitoring_keywords.verify_gnss_pty_data("/dev/ttyACM0")
