from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.ptp.system_ptp_parameter_keywords import SystemPTPParameterKeywords


@mark.p3
def test_ptp_parameter_modify_errors():
    """
    Test error scenarios for ptp-parameter-modify command.

    Test Steps:
        - Try to modify a parameter with non-existent id
        - Try to modify a parameter with invalid UUID

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_parameter_keywords = SystemPTPParameterKeywords(ssh_connection)

    # Use specified values
    non_existent_uuid = "00000000-0000-0000-0000-000000000001"
    invalid_uuid = "invalid_param"
    new_value = "2"

    get_logger().log_info("Trying to modify a parameter with non-existent id")
    error_message = system_ptp_parameter_keywords.system_ptp_parameter_modify_with_error(non_existent_uuid, new_value)
    validate_str_contains(error_message, f"No PTP parameter with id {non_existent_uuid} found", "Error message for non-existent parameter")

    get_logger().log_info("Trying to modify a parameter with invalid UUID")
    error_message = system_ptp_parameter_keywords.system_ptp_parameter_modify_with_error(invalid_uuid, new_value)
    validate_str_contains(error_message, "Invalid input for field/attribute uuid", "Error message for invalid UUID")
