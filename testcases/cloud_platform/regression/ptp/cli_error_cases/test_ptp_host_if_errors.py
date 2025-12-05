from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.ptp.system_host_if_ptp_keywords import SystemHostIfPTPKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_keywords import SystemPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_interface_keywords import SystemPTPInterfaceKeywords


@mark.p3
def test_host_if_ptp_assign_errors():
    """
    Test error scenarios for host-if-ptp-assign command.

    Test Steps:
        - Try to assign non-existent interface to host
        - Try to assign interface to non-existent host
        - Try to make already existent association more than once
        - Try to assign interface from non-existent ptp instance to host

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_host_if_ptp_keywords = SystemHostIfPTPKeywords(ssh_connection)
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)

    valid_hostname = "controller-0"
    host_name = valid_hostname.replace("-", "_")

    # Fetch interface from default.json5 using ConfigurationManager
    ptp_config = ConfigurationManager.get_ptp_config()
    valid_interface = ptp_config.get_host(host_name).get_nic("nic1").get_nic_connection().get_interface()

    valid_instance = "ptp7"
    valid_ptp_interface = "ptp7if1"
    non_existent_interface = "00000000-0000-0000-0000-000000000001"
    non_existent_hostname = "compute-100"
    non_existent_ptp_interface = "00000000-0000-0000-0000-000000000002"

    get_logger().log_info("Trying to assign non-existent interface to host")
    error_message = system_host_if_ptp_keywords.system_host_if_ptp_assign_with_error(valid_hostname, non_existent_interface, valid_ptp_interface)
    expected_error = f"Interface not found: host {valid_hostname} interface {non_existent_interface}"
    validate_str_contains(error_message, expected_error, "Error message for non-existent interface")

    get_logger().log_info("Trying to assign interface to non-existent host")
    error_message = system_host_if_ptp_keywords.system_host_if_ptp_assign_with_error(non_existent_hostname, valid_interface, valid_ptp_interface)
    expected_error = f"host not found: {non_existent_hostname}"
    validate_str_contains(error_message, expected_error, "Error message for non-existent host")

    # Create PTP instance
    get_logger().log_info(f"Creating PTP instance {valid_instance}")
    if "PTP instance not found" in system_ptp_instance_keywords.get_system_ptp_instance_show_with_error(valid_instance):
        system_ptp_instance_keywords.system_ptp_instance_add(valid_instance, "ptp4l")
    else:
        get_logger().log_info("Failed to create PTP instance or resources already exist")

    # Create PTP interface
    get_logger().log_info(f"Creating PTP interface {valid_ptp_interface}")
    if "PTP interface not found" in system_ptp_interface_keywords.get_system_ptp_interface_show_with_error(valid_ptp_interface):
        system_ptp_interface_keywords.system_ptp_interface_add(valid_ptp_interface, valid_instance)
    else:
        get_logger().log_info("Faled to create PTP interface or resources already exist")

    # Associate PTP to an interface at host.
    try:
        get_logger().log_info("Associate PTP to an interface at host")
        system_host_if_ptp_keywords.system_host_if_ptp_assign(valid_hostname, valid_interface, valid_ptp_interface)
    except Exception:
        get_logger().log_info("Association may already exist, continuing with test")

    get_logger().log_info("Trying to make already existent association more than once")
    error_message = system_host_if_ptp_keywords.system_host_if_ptp_assign_with_error(valid_hostname, valid_interface, valid_ptp_interface)
    expected_error = "PTP interface is already associated to interface"
    validate_str_contains(error_message, expected_error, "Error message for duplicate association")

    get_logger().log_info("Trying to assign interface from non-existent ptp instance to host")
    error_message = system_host_if_ptp_keywords.system_host_if_ptp_assign_with_error(valid_hostname, valid_interface, non_existent_ptp_interface)
    expected_error = f"PTP interface not found: {non_existent_ptp_interface}"
    validate_str_contains(error_message, expected_error, "Error message for non-existent PTP interface")


@mark.p3
def test_host_if_ptp_remove_errors():
    """
    Test error scenarios for host-if-ptp-remove command.

    Test Steps:
        - Try to remove non-existent interface from host
        - Try to remove interface from non-existent host
        - Try to remove interface from non-existent ptp instance

    Expected Results:
        - Appropriate error messages are returned for each scenario
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_host_if_ptp_keywords = SystemHostIfPTPKeywords(ssh_connection)
    system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
    system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)

    valid_instance = "ptp7"
    valid_ptp_interface = "ptp7if1"
    valid_hostname = "controller-0"
    host_name = valid_hostname.replace("-", "_")

    # Fetch interface from default.json5 using ConfigurationManager
    ptp_config = ConfigurationManager.get_ptp_config()
    valid_interface = ptp_config.get_host(host_name).get_nic("nic1").get_nic_connection().get_interface()

    valid_ptp_interface = "ptp7if1"
    non_existent_interface = "00000000-0000-0000-0000-000000000001"
    non_existent_hostname = "compute-100"
    non_existent_ptp_interface = "00000000-0000-0000-0000-000000000002"

    # Create PTP instance
    get_logger().log_info(f"Creating PTP instance {valid_instance}")
    if "PTP instance not found" in system_ptp_instance_keywords.get_system_ptp_instance_show_with_error(valid_instance):
        system_ptp_instance_keywords.system_ptp_instance_add(valid_instance, "ptp4l")
    else:
        get_logger().log_info("Failed to create PTP instance or resources already exist")

    # Create PTP interface
    get_logger().log_info(f"Creating PTP interface {valid_ptp_interface}")
    if "PTP interface not found" in system_ptp_interface_keywords.get_system_ptp_interface_show_with_error(valid_ptp_interface):
        system_ptp_interface_keywords.system_ptp_interface_add(valid_ptp_interface, valid_instance)
    else:
        get_logger().log_info("Faled to create PTP interface or resources already exist")

    get_logger().log_info("Trying to remove non-existent interface from host")
    error_message = system_host_if_ptp_keywords.system_host_if_ptp_remove_with_error(valid_hostname, non_existent_interface, valid_ptp_interface)
    expected_error = f"Interface not found: host {valid_hostname} interface {non_existent_interface}"
    validate_str_contains(error_message, expected_error, "Error message for non-existent interface")

    get_logger().log_info("Trying to remove interface from non-existent host")
    error_message = system_host_if_ptp_keywords.system_host_if_ptp_remove_with_error(non_existent_hostname, valid_interface, valid_ptp_interface)
    expected_error = f"host not found: {non_existent_hostname}"
    validate_str_contains(error_message, expected_error, "Error message for non-existent host")

    get_logger().log_info("Trying to remove interface from non-existent ptp instance")
    error_message = system_host_if_ptp_keywords.system_host_if_ptp_remove_with_error(valid_hostname, valid_interface, non_existent_ptp_interface)
    expected_error = f"PTP interface not found: {non_existent_ptp_interface}"
    validate_str_contains(error_message, expected_error, "Error message for non-existent PTP interface")
