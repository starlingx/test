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

def test_install_metrics_server():
    """
    Install (Upload and Apply) Application Metrics Server

    Raises:
        Exception: If application metrics-server failed to upload or apply
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    metrics_server_name = app_config.get_metric_server_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    # Verifies the app is not present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(metrics_server_name), False, f"The {metrics_server_name} application should not be already uploaded/applied on the system")

    # Setups the upload input object
    system_application_upload_input = SystemApplicationUploadInput()
    system_application_upload_input.set_app_name(metrics_server_name)
    system_application_upload_input.set_tar_file_path(f"{base_path}{metrics_server_name}*.tgz")

    # Uploads the app file and verifies it
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    metrics_server_app_status = system_applications.get_application(metrics_server_name).get_status()
    validate_equals(metrics_server_app_status, "uploaded", f"{metrics_server_name} upload status validation")

    # Applies the app to the active controller
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(metrics_server_name)

    # Verifies the app was applied
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, f"System application object should not be None")
    validate_equals(system_application_object.get_name(), metrics_server_name, f"Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"Application status validation")

def test_uninstall_metrics_server():
    """
    Uninstall (Remove and Delete) Application Metrics Server

    Raises:
        Exception: If application Metrics Server failed to remove or delete
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    metrics_server_name = app_config.get_metric_server_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    
    # Verifies if the app is not present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(metrics_server_name), True, f"The {metrics_server_name} application should be uploaded/applied on the system")

    # Removes the application
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(metrics_server_name)
    system_application_remove_input.set_force_removal(False)
    system_application_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)
    validate_equals(system_application_output.get_system_application_object().get_status(), SystemApplicationStatusEnum.UPLOADED.value, f"Application removal status validation")

    # Deletes the application
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(metrics_server_name)
    system_application_delete_input.set_force_deletion(False)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(delete_msg, f"Application {metrics_server_name} deleted.\n", f"Application deletion message validation")
