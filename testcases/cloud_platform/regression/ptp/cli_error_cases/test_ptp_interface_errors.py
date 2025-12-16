from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_keywords import SystemPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_interface_keywords import SystemPTPInterfaceKeywords


@mark.p3
def test_ptp_interface_add_errors():
    """
    Test error scenarios for ptp-interface-add command.

    Test Steps:
        - Try to add an interface to an invalid ptp instance

    Expected Results:
        - Appropriate error message is returned
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)

    valid_hostname = "controller-0"
    host_name = valid_hostname.replace("-", "_")

    # Fetch interface from default.json5 using ConfigurationManager
    ptp_config = ConfigurationManager.get_ptp_config()
    interface_name = ptp_config.get_host(host_name).get_nic("nic1").get_base_port()

    non_existent_instance = "no_ptp8"

    get_logger().log_info("Trying to add an interface to an invalid ptp instance")
    error_message = system_ptp_interface_keywords.system_ptp_interface_add_with_error(interface_name, non_existent_instance)
    validate_str_contains(error_message, f"PTP instance not found: {non_existent_instance}", "Error message for non-existent PTP instance")


@mark.p3
def test_ptp_interface_delete_errors():
    """
    Test error scenarios for ptp-interface-delete command.

    Test Steps:
        - Try to delete an interface that does not exist
        - Try to delete an interface with an invalid UUID

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)

    non_existent_uuid = "00000000-0000-0000-0000-000000000001"
    invalid_uuid = "invalid_uuid"

    get_logger().log_info("Trying to delete an interface that does not exist")
    error_message = system_ptp_interface_keywords.system_ptp_interface_delete_with_error(non_existent_uuid)
    validate_str_contains(error_message, f"PTP interface not found: {non_existent_uuid}", "Error message for non-existent interface")

    get_logger().log_info("Trying to delete an interface with an invalid UUID")
    error_message = system_ptp_interface_keywords.system_ptp_interface_delete_with_error(invalid_uuid)
    validate_str_contains(error_message, f"PTP interface not found: {invalid_uuid}", "Error message for invalid UUID")


@mark.p3
def test_ptp_interface_parameter_add_errors():
    """
    Test error scenarios for ptp-interface-parameter-add command.

    Test Steps:
        - Create PTP instance and interface
        - Try to add a bad keypair ptp-parameter to the interface
        - Trying to add a parameter using a non-existent interface name

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)

    invalid_parameter = "sma1"
    instance_name = "ptp7"
    interface_name = "ptp7if1"
    valid_parameter = "sma1=output"
    non_existent_interface = "non_existent_interface"

    # Create PTP instance and interface
    get_logger().log_info(f"Creating PTP instance {instance_name}")
    if "PTP instance not found" in system_ptp_instance_keywords.get_system_ptp_instance_show_with_error(instance_name):
        system_ptp_instance_keywords.system_ptp_instance_add(instance_name, "ptp4l")
    else:
        get_logger().log_info("Failed to create PTP instance or resources already exist")

    get_logger().log_info(f"Creating PTP interface {interface_name}")
    if "PTP interface not found" in system_ptp_interface_keywords.get_system_ptp_interface_show_with_error(interface_name):
        system_ptp_interface_keywords.system_ptp_interface_add(interface_name, instance_name)
    else:
        get_logger().log_info("Faled to create PTP interface or resources already exist")

    get_logger().log_info("Trying to add a bad keypair ptp-parameter to the interface")
    error_message = system_ptp_interface_keywords.system_ptp_interface_parameter_add_with_error(interface_name, invalid_parameter)
    validate_str_contains(error_message, f"Bad PTP parameter keypair: {invalid_parameter}", "Error message for bad key pair parameter")

    get_logger().log_info("Trying to add a parameter with non-existent using invalid interface name")
    error_message = system_ptp_interface_keywords.system_ptp_interface_parameter_add_with_error(non_existent_interface, valid_parameter)
    validate_str_contains(error_message, f"PTP interface not found: {non_existent_interface}", "Error message for invalid interface name")


@mark.p3
def test_ptp_interface_show_errors():
    """
    Test error scenarios for ptp-interface-show command.

    Test Steps:
        - Try to show an interface with invalid UUID
        - Try to show an interface with non-existent UUID

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)

    invalid_uuid = "invalid_uuid"
    non_existent_uuid = "00000000-0000-0000-0000-000000000001"

    get_logger().log_info("Trying to show an interface with invalid UUID")
    error_message = system_ptp_interface_keywords.get_system_ptp_interface_show_with_error(invalid_uuid)
    validate_str_contains(error_message, f"PTP interface not found: {invalid_uuid}", "Error message for invalid UUID")

    get_logger().log_info("Trying to show an interface with non-existent UUID")
    error_message = system_ptp_interface_keywords.get_system_ptp_interface_show_with_error(non_existent_uuid)
    validate_str_contains(error_message, f"PTP interface not found: {non_existent_uuid}", "Error message for non-existent interface")


@mark.p3
def test_ptp_interface_parameter_delete_errors():
    """
    Test error scenarios for ptp-interface-parameter-delete command.

    Test Steps:
        - Try to delete an interface parameter with non-existent interface UUID
        - Try to delete an interface parameter with invalid parameter UUID

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)

    non_existent_uuid = "00000000-0000-0000-0000-000000000001"
    invalid_parameter = "sma1"
    valid_parameter = "sma1=output"
    instance_name = "ptp7"
    interface_name = "ptp7if1"

    # Create PTP instance and interface
    get_logger().log_info(f"Creating PTP instance {instance_name}")
    if "PTP instance not found" in system_ptp_instance_keywords.get_system_ptp_instance_show_with_error(instance_name):
        system_ptp_instance_keywords.system_ptp_instance_add(instance_name, "ptp4l")
    else:
        get_logger().log_info("Failed to create PTP instance or resources already exist")

    get_logger().log_info(f"Creating PTP interface {interface_name}")
    if "PTP interface not found" in system_ptp_interface_keywords.get_system_ptp_interface_show_with_error(interface_name):
        system_ptp_interface_keywords.system_ptp_interface_add(interface_name, instance_name)
    else:
        get_logger().log_info("Faled to create PTP interface or resources already exist")

    get_logger().log_info(f"Adding PTP interface parameter {interface_name}")
    if valid_parameter not in system_ptp_interface_keywords.get_system_ptp_interface_show(interface_name).get_ptp_interface().get_parameters():
        system_ptp_interface_keywords.system_ptp_interface_parameter_add(interface_name, valid_parameter)
    else:
        get_logger().log_info("Faled to create PTP interface or resources already exist")

    get_logger().log_info("Trying to delete an interface parameter with non-existent interface UUID")
    error_message = system_ptp_interface_keywords.system_ptp_interface_parameter_delete_with_error(non_existent_uuid, valid_parameter)
    validate_str_contains(error_message, f"PTP interface not found: {non_existent_uuid}", "Error message for non-existent interface")

    get_logger().log_info("Trying to delete an interface parameter with invalid parameter")
    valid_uuid = system_ptp_interface_keywords.get_system_ptp_interface_show(interface_name).get_ptp_interface().get_uuid()
    error_message = system_ptp_interface_keywords.system_ptp_interface_parameter_delete_with_error(valid_uuid, invalid_parameter)
    validate_str_contains(error_message, f"Bad PTP parameter keypair: {invalid_parameter}", "Error message for invalid parameter")
