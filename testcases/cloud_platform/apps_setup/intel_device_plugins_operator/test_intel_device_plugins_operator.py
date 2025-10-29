from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords

from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum

from framework.validation.validation import validate_equals, validate_not_equals

from framework.logging.automation_logger import get_logger


def test_install_intel_device_plugins():
    """
    Install (Upload and Apply) Intel Device Plugins

    Raises:
        Exception: If application Intel Device Plugins failed to upload or apply
    """

    # Setup app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()

    nfd_name = app_config.get_node_feature_discovery_app_name()
    nfd_file_path = f"{base_path}{nfd_name}*.tgz"

    intel_device_plugins_name = app_config.get_intel_device_plugins_app_name()
    intel_device_plugins_file_path = f"{base_path}{intel_device_plugins_name}*.tgz"

    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    get_logger().log_test_case_step('Install Node Feature Discovery first')
    # If NFD is not already installed, install it
    nfd_status = SystemApplicationApplyKeywords(ssh_connection).is_already_applied(nfd_name)
    if not nfd_status:
        get_logger().log_info('NFD not installed. Installing...')
        nfd_app_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload_and_apply_app(nfd_name, nfd_file_path)
        nfd_app_object = nfd_app_output.get_system_application_object()
        validate_equals(nfd_app_object.get_name(), nfd_name, f"{nfd_name} name validation")
        validate_equals(nfd_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{nfd_name} application status validation")
    else:
        validate_not_equals(nfd_status, None,
                            "NFD application should be in applied state")

    get_logger().log_test_case_step('Install Intel Device Plugins')
    # Verify the Intel Device Plugin app is not present in the system
    intel_device_plugins_status = SystemApplicationApplyKeywords(ssh_connection).is_already_applied(intel_device_plugins_name)
    if not intel_device_plugins_status:
        get_logger().log_info('Intel Device Plugins not installed. Installing...')
        intel_device_plugins_app_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload_and_apply_app(intel_device_plugins_name, intel_device_plugins_file_path)
        intel_device_plugins_app_object = intel_device_plugins_app_output.get_system_application_object()
        validate_equals(intel_device_plugins_app_object.get_name(), intel_device_plugins_name, f"{intel_device_plugins_name} name validation")
        validate_equals(intel_device_plugins_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{intel_device_plugins_name} application status validation")
    else:
        validate_not_equals(intel_device_plugins_status, None,
                            " Intel Device Plugin application should be in applied state")


def test_uninstall_intel_device_plugins():
    """
    Uninstall (Remove and Delete) Application Intel Device Plugin

    Raises:
        Exception: If application Intel Device Plugin failed to remove or delete
    """
    # Setup app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    intel_device_plugins_name = app_config.get_intel_device_plugins_app_name()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    get_logger().log_test_case_step('Uninstall Intel Device Plugin first (since it depends on NFD)')
    # Verify if the  Intel Device Plugin app already present in the system
    intel_device_plugins_status = SystemApplicationApplyKeywords(ssh_connection).is_already_applied(intel_device_plugins_name)
    if intel_device_plugins_status:
        get_logger().log_info('Intel Device Plugins installed. Removing...')
        remove_delete_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(intel_device_plugins_name)
        validate_equals(remove_delete_output, f"Application {intel_device_plugins_name} deleted.\n",
                        "Intel Device Plugin deletion validation")
    else:
        validate_not_equals(intel_device_plugins_status, None,
                            "Intel Device Plugins application should be in applied state")

    get_logger().log_test_case_step('Uninstall Node Feature Discovery')
    # Verify if the  Intel Device Plugin app already present in the system
    nfd_status = SystemApplicationApplyKeywords(ssh_connection).is_already_applied(nfd_name)
    if nfd_status:
        get_logger().log_info('NFD installed. Removing...')
        remove_delete_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(nfd_name)
        validate_equals(remove_delete_output, f"Application {nfd_name} deleted.\n",
                        "NFD deletion validation")
    else:
        validate_not_equals(nfd_status, None,
                            "NFD application should be in applied state")
