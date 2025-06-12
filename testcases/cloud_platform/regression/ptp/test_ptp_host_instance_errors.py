from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.ptp.system_host_ptp_instance_keywords import SystemHostPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_keywords import SystemPTPInstanceKeywords


@mark.p3
def test_host_ptp_instance_assign_errors():
    """
    Test error scenarios for host-ptp-instance-assign command.

    Test Steps:
        - Try to assign instance to a non-existent host
        - Try to assign non-existent instance to a host
        - Try to assign instance to a host more than once

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)

    valid_hostname = "controller-0"
    valid_instance = "ptp7"
    non_existent_hostname = "compute-100"
    non_existent_instance = "no_ptp8"

    # Create PTP instance
    get_logger().log_info(f"Creating PTP instance {valid_instance}")
    if "PTP instance not found" in system_ptp_instance_keywords.get_system_ptp_instance_show_with_error(valid_instance):
        system_ptp_instance_keywords.system_ptp_instance_add(valid_instance, "ptp4l")
    else:
        get_logger().log_info("Failed to create PTP instance or resources already exist")

    get_logger().log_info("Trying to assign instance to a non-existent host")
    error_message = system_host_ptp_instance_keywords.system_host_ptp_instance_assign_with_error(non_existent_hostname, valid_instance)
    validate_str_contains(error_message, f"host not found: {non_existent_hostname}", "Error message for non-existent host")

    get_logger().log_info("Trying to assign non-existent instance to a host")
    error_message = system_host_ptp_instance_keywords.system_host_ptp_instance_assign_with_error(valid_hostname, non_existent_instance)
    validate_str_contains(error_message, f"PTP instance not found: {non_existent_instance}", "Error message for non-existent instance")

    try:
        get_logger().log_info("Creating initial association")
        system_host_ptp_instance_keywords.system_host_ptp_instance_assign(valid_hostname, valid_instance)
    except Exception:
        get_logger().log_info("Association may already exist, continuing with test")

    get_logger().log_info("Trying to assign instance to a host more than once")
    error_message = system_host_ptp_instance_keywords.system_host_ptp_instance_assign_with_error(valid_hostname, valid_instance)
    validate_str_contains(error_message, "PTP instance is already associated to host", "Error message for duplicate association")


@mark.p3
def test_host_ptp_instance_remove_errors():
    """
    Test error scenarios for host-ptp-instance-remove command.

    Test Steps:
        - Try to remove instance from non-existent host
        - Try to remove non-existent instance from host

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)

    # Use specified values
    valid_hostname = "controller-0"
    valid_instance = "ptp7"
    non_existent_hostname = "compute-100"
    non_existent_instance = "no_ptp8"

    get_logger().log_info("Trying to remove instance from non-existent host")
    error_message = system_host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error(non_existent_hostname, valid_instance)
    validate_str_contains(error_message, f"host not found: {non_existent_hostname}", "Error message for non-existent host")

    get_logger().log_info("Trying to remove non-existent instance from host")
    error_message = system_host_ptp_instance_keywords.system_host_ptp_instance_remove_with_error(valid_hostname, non_existent_instance)
    validate_str_contains(error_message, f"PTP instance not found: {non_existent_instance}", "Error message for non-existent instance")
