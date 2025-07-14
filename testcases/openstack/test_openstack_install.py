from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords


def test_openstack_install():
    """
    Test to install and uninstall the OpenStack application

    Test Steps:
        - connect to active controller
        - check application status
        - Uninstall the existing application
        - Install the specified version of the application

    """
    get_logger().log_info("App Install Step")
    # Setups the upload input object.
    system_application_upload_input = SystemApplicationUploadInput()
    app_name = ConfigurationManager.get_openstack_config().get_app_name()
    system_application_upload_input.set_app_name(app_name)
    if ConfigurationManager.get_openstack_config().get_remote_config().get_enabled_flag():
        system_application_upload_input.set_app_version(ConfigurationManager.get_openstack_config().get_remote_config().get_app_version())
        system_application_upload_input.set_automatic_installation(False)
    elif ConfigurationManager.get_openstack_config().get_custom_config().get_enabled_flag():
        system_application_upload_input.set_tar_file_path(ConfigurationManager.get_openstack_config().get_custom_config().get_file_path())
        system_application_upload_input.set_force(True)
    # Setups app configs and lab connection
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    status_list = [SystemApplicationStatusEnum.UPLOADED.value, SystemApplicationStatusEnum.APPLIED.value, SystemApplicationStatusEnum.UPLOAD_FAILED.value, SystemApplicationStatusEnum.APPLY_FAILED.value]
    # if uploading or applying or removing or deleting, wait to complete
    app_status = "Not Uploaded or Applied"
    if SystemApplicationListKeywords(ssh_connection).is_app_present(app_name):
        app_status = SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, status_list)
        get_logger().log_info(f"{app_name} Status is {app_status}")

    get_logger().log_info(f"{app_name} Status is {app_status}")
    get_logger().log_info("Uploading & Installing Openstack application")
    system_application_upload_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)

    # Asserts that the uploading process concluded successfully
    system_application_object = system_application_upload_output.get_system_application_object()
    assert system_application_object is not None, f"Expecting 'system_application_object' as not None, Observed: {system_application_object}."
    assert system_application_object.get_name() == app_name, f"Expecting 'app_name' = {app_name}, Observed: {system_application_object.get_name()}."
    assert system_application_object.get_status() == SystemApplicationStatusEnum.UPLOADED.value, f"Expecting 'system_application_object.get_status()' = {SystemApplicationStatusEnum.UPLOADED.value}, Observed: {system_application_object.get_status()}."

    # Asserts that the applying process concluded successfully
    # Executes the application installation
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name, 3600, 30)
    system_application_object = system_application_apply_output.get_system_application_object()
    assert system_application_object is not None, f"Expecting 'system_application_object' as not None, Observed: {system_application_object}."
    assert system_application_object.get_name() == app_name, f"Expecting 'app_name' = {app_name}, Observed: {system_application_object.get_name()}."
    assert system_application_object.get_status() == SystemApplicationStatusEnum.APPLIED.value, f"Expecting 'system_application_object.get_status()' = {SystemApplicationStatusEnum.APPLIED.value}, Observed: {system_application_object.get_status()}."
