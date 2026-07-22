from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from config.configuration_manager import ConfigurationManager


@mark.p2
def test_check_status_and_version_nginx_ingress_controller_app():
    """
    Verify nginx-ingress-controller application is applied and the version matches.

    Test Steps:
        - Verify nginx-ingress-controller application is present in the system application list
        - Validate nginx-ingress-controller application status is 'applied' and the version matches.
    """
    platform_version = CloudPlatformVersionManagerClass().get_sw_version().get_name()
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_config = ConfigurationManager.get_app_config()
    nginx_ingress_controller_name = app_config.get_nginx_ingress_controller_name()

    get_logger().log_test_case_step("Verify nginx-ingress-controller app is present, applied, and the version matches.")
    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    app_list_keywords.validate_app_status(nginx_ingress_controller_name, "applied")
    app_list_keywords.validate_app_version(nginx_ingress_controller_name, platform_version)

    app_show_output = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(nginx_ingress_controller_name)
    app_version = app_show_output.get_system_application_object().get_version()
    get_logger().log_info(f"nginx-ingress-controller version {app_version}")