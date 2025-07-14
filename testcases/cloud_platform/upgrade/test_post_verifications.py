from config.configuration_manager import ConfigurationManager

from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords

def test_post_upgrade_verification_metrics_server():
    """
    Verification for successful Metrics Server upgrade after a system upgrade

    Raises:
        Exception: If application Metrics Server fails to be in the desired states (in the lab, applied and upgraded)
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    metrics_server_name = app_config.get_metric_server_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)
    system_applications = app_list_keywords.get_system_application_list()

    # Verifies the app is in the lab
    validate_equals(system_applications.is_in_application_list(metrics_server_name), True,  f"{metrics_server_name} application should be in the lab")

    # Verifies the app is applied
    metrics_server_app_info = system_applications.get_application(metrics_server_name)
    app_status = metrics_server_app_info.get_status()
    validate_equals(app_status, 'applied', f"{metrics_server_name} application should be applied after upgrade")

    # Verifies the app is upgraded
    progress_message = metrics_server_app_info.get_progress()
    app_version = metrics_server_app_info.get_version()
    expected_pattern = "Application update from version"
    validate_str_contains(progress_message, expected_pattern, f"{metrics_server_name} application should be upgraded to the version {app_version}")


def test_post_upgrade_verification_istio():
    """
    Verification for successful Istio upgrade after a system upgrade

    Raises:
        Exception: If application Istio fails to be in the desired states (in the lab, applied and upgraded)
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    istio_name = app_config.get_istio_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)
    system_applications = app_list_keywords.get_system_application_list()

    # Verifies the app is in the lab
    validate_equals(system_applications.is_in_application_list(istio_name), True,  f"{istio_name} application should be in the lab")

    # Verifies the app is applied
    istio_app_info = system_applications.get_application(istio_name)
    app_status = istio_app_info.get_status()
    validate_equals(app_status, 'applied', f"{istio_name} application should be applied after upgrade")

    # Verifies the app is upgraded
    progress_message = istio_app_info.get_progress()
    app_version = istio_app_info.get_version()
    expected_pattern = "Application update from version"
    validate_str_contains(progress_message, expected_pattern, f"{istio_name} application should be upgraded to the version {app_version}")


def test_post_upgrade_verification_kubernetes_power_manager():
    """
    Verification for successful Kubernetes Power Manager upgrade after a system upgrade

    Raises:
        Exception: If application Kubernetes Power Manager fails to be in the desired states (in the lab, applied and upgraded)
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    power_manager_name = app_config.get_power_manager_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)
    system_applications = app_list_keywords.get_system_application_list()

    # Verifies the app is in the lab
    validate_equals(system_applications.is_in_application_list(power_manager_name), True,
                   f"{power_manager_name} application should be in the lab")

    # Verifies the app is applied
    power_manager_app_info = system_applications.get_application(power_manager_name)
    app_status = power_manager_app_info.get_status()
    validate_equals(app_status, 'applied', f"{power_manager_name} application should be applied after upgrade")

    # Verifies the app is upgraded
    progress_message = power_manager_app_info.get_progress()
    app_version = power_manager_app_info.get_version()
    expected_pattern = "Application update from version"
    validate_str_contains(progress_message, expected_pattern,
                         f"{power_manager_name} application should be upgraded to the version {app_version}")