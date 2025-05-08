import os

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.ptp.ptp_setup_executor_keywords import PTPSetupExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_teardown_executor_keywords import PTPTeardownExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_verify_config_keywords import PTPVerifyConfigKeywords
from keywords.files.file_keywords import FileKeywords


@mark.p0
@mark.lab_has_standby_controller
def test_delete_and_add_all_ptp_configuration():
    """
    Delete and Add all PTP configurations
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    get_logger().log_info("Delete all PTP configuration")
    ptp_teardown_keywords = PTPTeardownExecutorKeywords(ssh_connection)
    ptp_teardown_keywords.delete_all_ptp_configurations()

    get_logger().log_info("Add all PTP configuration")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_setup_template.json5")
    ptp_setup_keywords = PTPSetupExecutorKeywords(ssh_connection, ptp_setup_template_path)
    ptp_setup_keywords.add_all_ptp_configurations()


@mark.p0
@mark.lab_has_compute
def test_delete_and_add_all_ptp_configuration_for_compute():
    """
    Delete and Add all PTP configurations
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    get_logger().log_info("Delete all PTP configuration")
    ptp_teardown_keywords = PTPTeardownExecutorKeywords(ssh_connection)
    ptp_teardown_keywords.delete_all_ptp_configurations()

    get_logger().log_info("Add all PTP configuration")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")
    ptp_setup_keywords = PTPSetupExecutorKeywords(ssh_connection, ptp_setup_template_path)
    ptp_setup_keywords.add_all_ptp_configurations()

    get_logger().log_info("Verify all PTP configuration")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup_template_path)
    ptp_verify_config_keywords.verify_all_ptp_configurations()

    local_file_path = os.path.join(get_logger().get_test_case_log_dir(), "user.log")
    FileKeywords(ssh_connection).download_file("/var/log/user.log", local_file_path)
