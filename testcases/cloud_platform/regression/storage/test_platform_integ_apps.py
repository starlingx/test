from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords


def setup(request, active_ssh_connection):
    """Setup function to ensure platform-integ-apps is applied before tests."""
    app_config = ConfigurationManager.get_app_config()
    platform_integ_apps_name = app_config.get_platform_integ_apps_app_name()
    get_logger().log_setup_step("Checking ceph health.")
    ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)
    get_logger().log_setup_step("Check app platform-integ-apps is applied.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(platform_integ_apps_name, "applied")

    def cleanup():
        if not SystemApplicationListKeywords(active_ssh_connection).is_app_present(platform_integ_apps_name):
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)
        get_logger().log_teardown_step("Checking ceph health.")
        ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
        ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    request.addfinalizer(cleanup)
    return platform_integ_apps_name


@mark.p2
def test_remove_apply_platform_integ_app(request):
    """
    Remove and apply the platform-integ-apps  application.
    Test Steps:
        - Run this command "system application-remove platform-integ-apps"
        - The status of the application should change to uploaded
        - Run this command "system application-apply"
        - The platform-integ-apps application was applied
    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)
    get_logger().log_test_case_step("Remove platform-integ-apps")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(platform_integ_apps_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Apply platform-integ-apps")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)


@mark.p2
def test_delete_platform_integ_app(request):
    """
    Delete platform-integ-apps application.
    Test Steps:
        - Run this command "system application-remove platform-integ-apps"
        - The status of the application should change to uploaded
        - Run this command "system application-delete"
        - The platform-integ-apps application was deleted
    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Test- Testdown: Upload platform-integ-apps")
        app_config = ConfigurationManager.get_app_config()
        base_path = app_config.get_base_application_path()
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(platform_integ_apps_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{platform_integ_apps_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)
        get_logger().log_teardown_step("Apply platform-integ-apps")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)

    request.addfinalizer(teardown)
    get_logger().log_test_case_step("Remove platform-integ-apps")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(platform_integ_apps_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Delete platform-integ-apps")
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(platform_integ_apps_name)
    app_delete_response = SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(app_delete_response.rstrip(), "Application platform-integ-apps deleted.", "Application deletion.")
