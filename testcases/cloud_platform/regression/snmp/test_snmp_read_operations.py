from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.snmp.snmp_keywords import SNMPKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p3
def test_snmp_read_operations_v3(request):
    """Test SNMP read operations with v3 on active controller.

    Test Steps:
        - Install SNMP application
        - Generate test alarm
        - Execute SNMP get command
        - Execute SNMP walk command
        - Verify alarm ID in output

    Teardown:
        - Clean up test alarms
        - Remove SNMP application
    """

    def cleanup_snmp():
        """Clean up SNMP test resources."""
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        snmp_keywords = SNMPKeywords(ssh_connection)
        alarm_removed = snmp_keywords.remove_test_alarm()
        if not alarm_removed:
            get_logger().log_info("Alarm removal failed - alarm may not exist")
        snmp_keywords.remove_and_cleanup_snmp()
        get_logger().log_info("SNMP cleanup completed")

    request.addfinalizer(cleanup_snmp)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    snmp_keywords = SNMPKeywords(ssh_connection)
    config = ConfigurationManager.get_snmp_config()

    get_logger().log_info("Installing SNMP application")
    snmp_keywords.install_and_configure_snmp()

    get_logger().log_info("Generating test alarm")
    snmp_keywords.generate_test_alarm()

    lab_config = ConfigurationManager.get_lab_config()
    controller_ip = lab_config.get_floating_ip()

    get_logger().log_info("Executing SNMP get command")
    alarm_oid = snmp_keywords.get_next_alarm_oid()

    found_alarm = snmp_keywords.wait_for_alarm_in_snmp(alarm_oid, controller_ip, timeout=60, version="v3")
    validate_equals(found_alarm, True, "SNMP get operation did not find alarm within timeout")

    get_logger().log_info("Executing SNMP walk command")
    walk_output = snmp_keywords.snmp_walk(config.get_active_alarm_oid(), controller_ip, version="v3")
    walk_result = walk_output.get_snmp_object()

    get_logger().log_info(f"SNMP walk result: {walk_result.get_content()}")

    validate_equals(walk_output.is_success(), True, "SNMP walk command failed")
    validate_str_contains(walk_result.get_content(), config.get_trap_alarm_id(), f"Alarm ID {config.get_trap_alarm_id()} not found via SNMP walk command")
