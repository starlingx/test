from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from config.configuration_manager import ConfigurationManager


@mark.p2
def test_cert_manager_app_check_status_and_version():
    """
    Verify cert-manager application status is applied and the version matches.

    Test Steps:
        - Verify cert-manager application is present in the system application list
        - Validate cert-manager application status is 'applied' and the version matches.
    """
    platform_version = CloudPlatformVersionManagerClass().get_sw_version().get_name()
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_config = ConfigurationManager.get_app_config()
    cert_manager_name = app_config.get_cert_manager_name()
    
    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    get_logger().log_test_case_step("Validate cert-manager is present and applied, and the version matches.")
    app_list_keywords.validate_app_status(cert_manager_name, "applied")
    app_list_keywords.validate_app_version(cert_manager_name, platform_version)

    app_show_output = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(cert_manager_name)
    app_version = app_show_output.get_system_application_object().get_version()
    get_logger().log_info(f"cert-manager version: {app_version}")