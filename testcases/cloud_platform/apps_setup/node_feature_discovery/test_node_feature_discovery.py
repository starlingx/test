from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords

from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from framework.validation.validation import validate_equals, validate_not_equals
from framework.logging.automation_logger import get_logger

def test_install_nfd():
    """
    Install application Node Feature Discovery

    Raises:
        Exception: If application node-feature-discovery failed to upload or apply
    """
    # Setup app configs and lab connection
    get_logger().log_test_case_step("Setup app configs and lab connection")
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Check if NFD is already applied usando SystemApplicationApplyKeywords
    get_logger().log_test_case_step(f"Checking if {nfd_name} is already applied")
    apply_keywords = SystemApplicationApplyKeywords(ssh_connection)
    if apply_keywords.is_already_applied(nfd_name):
        get_logger().log_info(f"{nfd_name} is already applied on the system. No action required.")
        return

    # If not applied, upload and apply
    get_logger().log_test_case_step(f"{nfd_name} not found/applied. Uploading...")
    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name(nfd_name)
    upload_input.set_tar_file_path(f"{base_path}{nfd_name}*.tgz")
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)

    # Apply the application
    get_logger().log_test_case_step(f"Applying {nfd_name} application")
    apply_output = apply_keywords.system_application_apply(nfd_name)
    app_obj = apply_output.get_system_application_object()

    # Validations
    get_logger().log_test_case_step("Validating application object and status")
    validate_not_equals(app_obj, None, "NFD application object should not be None")
    validate_equals(app_obj.get_name(), nfd_name, "NFD application name validation")
    validate_equals(app_obj.get_status(), SystemApplicationStatusEnum.APPLIED.value, "NFD application status validation")
    get_logger().log_info(f"{nfd_name} successfully uploaded and applied.")


def test_uninstall_nfd():
    """
    Uninstall (Remove and Delete) Application Node Feature Discovery

    Raises:
        Exception: If application Node Feature Discovery failed to remove or delete
    """
    # Setup app configs and lab connection
    get_logger().log_test_case_step("Setup app configs and lab connection")
    app_config = ConfigurationManager.get_app_config()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Verify if NFD is installed before uninstalling
    get_logger().log_test_case_step(f"Verifying if {nfd_name} is applied before uninstalling")
    apply_keywords = SystemApplicationApplyKeywords(ssh_connection)
    if not apply_keywords.is_already_applied(nfd_name):
        raise Exception(f"{nfd_name} is not applied, cannot uninstall.")

    # Get current status of the application
    app_list = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    app_obj = app_list.get_application(nfd_name)
    current_status = app_obj.get_status()

    if current_status == SystemApplicationStatusEnum.UPLOADED.value:
        # If status is UPLOADED, skip remove and go directly to delete
        get_logger().log_info(f"{nfd_name} is in UPLOADED state, proceeding directly to delete.")
    else:
        # If status is not UPLOADED, perform remove first
        get_logger().log_test_case_step(f"Removing {nfd_name} application")
        remove_input = SystemApplicationRemoveInput()
        remove_input.set_app_name(nfd_name)
        remove_input.set_force_removal(True)
        remove_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(remove_input)

        # Validations
        get_logger().log_test_case_step("Validating removal status")
        validate_equals(
            remove_output.get_system_application_object().get_status(),
            SystemApplicationStatusEnum.UPLOADED.value,
            "Application removal status validation"
        )

    # Delete the application
    get_logger().log_test_case_step(f"Deleting {nfd_name} application")
    delete_input = SystemApplicationDeleteInput()
    delete_input.set_app_name(nfd_name)
    delete_input.set_force_deletion(False)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(delete_input)

    # Validations
    get_logger().log_test_case_step("Validating deletion message")
    validate_equals(delete_msg, f"Application {nfd_name} deleted.\n", "Application deletion message validation")
    get_logger().log_info(f"{nfd_name} successfully removed and deleted.")