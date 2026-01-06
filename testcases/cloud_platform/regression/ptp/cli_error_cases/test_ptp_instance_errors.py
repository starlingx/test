from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_keywords import SystemPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_parameter_keywords import SystemPTPInstanceParameterKeywords


@mark.p3
def test_ptp_instance_add_errors():
    """
    Test error scenarios for ptp-instance-add command.

    Test Steps:
        - Try to create a ptp-instance of invalid type

    Expected Results:
        - Appropriate error message is returned
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)

    instance_name = "ptp7"
    invalid_type = "random"

    get_logger().log_info("Trying to create a ptp-instance of invalid type")
    error_message = system_ptp_instance_keywords.system_ptp_instance_add_with_error(instance_name, invalid_type)
    validate_str_contains(error_message, "usage: system ptp-instance-add", "Error message for invalid PTP instance type")


@mark.p3
def test_ptp_instance_delete_errors():
    """
    Test error scenarios for ptp-instance-delete command.

    Test Steps:
        - Try to delete a non-existent ptp-instance

    Expected Results:
        - Appropriate error message is returned
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)

    non_existent_instance = "no_ptp8"

    get_logger().log_info("Trying to delete a non-existent ptp-instance")
    error_message = system_ptp_instance_keywords.system_ptp_instance_delete_with_error(non_existent_instance)
    validate_str_contains(error_message, f"PTP instance not found: {non_existent_instance}", "Error message for non-existent PTP instance")


@mark.p3
def test_ptp_instance_show_errors():
    """
    Test error scenarios for ptp-instance-show command.

    Test Steps:
        - Try to show info from a non-existent ptp-instance

    Expected Results:
        - Appropriate error message is returned
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)

    non_existent_instance = "no_ptp8"

    get_logger().log_info("Trying to show info from a non-existent ptp-instance")
    error_message = system_ptp_instance_keywords.get_system_ptp_instance_show_with_error(non_existent_instance)
    validate_str_contains(error_message, f"PTP instance not found: {non_existent_instance}", "Error message for non-existent PTP instance")


@mark.p3
def test_ptp_instance_parameter_delete_errors():
    """
    Test error scenarios for ptp-instance-parameter-delete command.

    Test Steps:
        - Try to delete parameter from an invalid instance
        - Try to delete parameter with an invalid parameter UUID

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    system_ptp_instance_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)

    invalid_instance = "no_ptp8"
    valid_instance = "ptp7"
    invalid_parameter = "invalid_param"

    # Create PTP instance and interface
    get_logger().log_info(f"Creating PTP instance {valid_instance}")
    if "PTP instance not found" in system_ptp_instance_keywords.get_system_ptp_instance_show_with_error(valid_instance):
        system_ptp_instance_keywords.system_ptp_instance_add(valid_instance, "ptp4l")
    else:
        get_logger().log_info("Failed to create PTP instance or resources already exist")

    get_logger().log_info("Trying to delete parameter from an invalid instance")
    error_message = system_ptp_instance_parameter_keywords.system_ptp_instance_parameter_delete_with_error(invalid_instance, "param")
    validate_str_contains(error_message, f"PTP instance not found: {invalid_instance}", "Error message for invalid instance")

    get_logger().log_info("Trying to delete parameter with an invalid parameter UUID")
    error_message = system_ptp_instance_parameter_keywords.system_ptp_instance_parameter_delete_with_error(valid_instance, invalid_parameter)
    validate_str_contains(error_message, f"Bad PTP parameter keypair: {invalid_parameter}", "Error message for invalid parameter")


@mark.p3
def test_ptp_instance_parameter_add_errors():
    """
    Test error scenarios for ptp-instance-parameter-add command.

    Test Steps:
        - Try to add a parameter to an invalid instance
        - Try to add an invalid parameter

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    system_ptp_instance_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)

    invalid_instance = "no_ptp8"
    valid_instance = "ptp7"
    invalid_parameter = "invalid_param"

    # Create PTP instance and interface
    get_logger().log_info(f"Creating PTP instance {valid_instance}")
    if "PTP instance not found" in system_ptp_instance_keywords.get_system_ptp_instance_show_with_error(valid_instance):
        system_ptp_instance_keywords.system_ptp_instance_add(valid_instance, "ptp4l")
    else:
        get_logger().log_info("Failed to create PTP instance or resources already exist")

    get_logger().log_info("Trying to add a parameter to an invalid instance")
    error_message = system_ptp_instance_parameter_keywords.system_ptp_instance_parameter_add_with_error(invalid_instance, "param=value")
    validate_str_contains(error_message, f"PTP instance not found: {invalid_instance}", "Error message for invalid instance")

    get_logger().log_info("Trying to add an invalid parameter")
    error_message = system_ptp_instance_parameter_keywords.system_ptp_instance_parameter_add_with_error(valid_instance, invalid_parameter)
    validate_str_contains(error_message, f"Bad PTP parameter keypair: {invalid_parameter}", "Error message for invalid parameter")
