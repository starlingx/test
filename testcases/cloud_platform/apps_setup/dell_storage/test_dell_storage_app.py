from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_abort_keywords import SystemApplicationAbortKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords


@mark.p2
def test_pre_upgrade_check_dell_storage_app():
    """
    Check ceph health and ensure the dell-storage application is applied.

    Test Steps:
        - Verify ceph health status is healthy
        - Check if dell-storage application is present and applied
        - Upload and apply dell-storage if not present
        - Apply dell-storage if present but not in applied state
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_config = ConfigurationManager.get_app_config()
    dell_storage_name = app_config.get_dell_storage_app_name()
    base_path = app_config.get_base_application_path()

    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(active_ssh_connection).wait_for_ceph_health_status(expect_health_status=True)

    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    if not app_list_keywords.is_app_present(dell_storage_name):
        get_logger().log_test_case_step("Upload dell-storage app.")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(dell_storage_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{dell_storage_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

        get_logger().log_test_case_step("Apply dell-storage app.")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=dell_storage_name)
    else:
        app_show = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(dell_storage_name)
        app_status = app_show.get_system_application_object().get_status()
        if app_status != "applied":
            get_logger().log_test_case_step("Apply dell-storage app.")
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=dell_storage_name)


@mark.p2
def test_post_upgrade_check_dell_storage_app():
    """
    Verify ceph health and dell-storage application status after upgrade, then remove, apply, abort, and re-apply.

    Test Steps:
        - Verify ceph health status is healthy
        - Validate the dell-storage application is present and in applied state
        - Remove the dell-storage application using "system application-remove"
        - Apply the dell-storage application without waiting for completion
        - Abort the dell-storage application using "system application-abort"
        - Validate the application status changed to apply-failed
        - Apply the dell-storage application again to ensure it can be applied after aborting
        - Verify ceph health status is healthy
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dell_storage_name = ConfigurationManager.get_app_config().get_dell_storage_app_name()

    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(active_ssh_connection).wait_for_ceph_health_status(expect_health_status=True)

    get_logger().log_test_case_step("Validate dell-storage app is applied.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(dell_storage_name, "applied")

    get_logger().log_test_case_step("Remove dell-storage.")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(dell_storage_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Apply dell-storage.")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=dell_storage_name, wait_for_applied=False)

    get_logger().log_test_case_step("Abort dell-storage.")
    SystemApplicationAbortKeywords(active_ssh_connection).system_application_abort(app_name=dell_storage_name)

    get_logger().log_test_case_step("Validate application status changed to apply-failed.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(dell_storage_name, "apply-failed")

    get_logger().log_test_case_step("Apply dell-storage.")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=dell_storage_name)

    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(active_ssh_connection).wait_for_ceph_health_status(expect_health_status=True)
