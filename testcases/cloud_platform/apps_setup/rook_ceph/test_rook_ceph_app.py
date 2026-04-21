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
@mark.lab_has_rook_ceph
def test_pre_upgrade_check_rook_ceph_app():
    """
    Check ceph health and ensure the rook-ceph application is applied.

    Test Steps:
        - Verify ceph health status is healthy
        - Check if rook-ceph application is present and applied
        - Upload and apply rook-ceph if not present
        - Apply rook-ceph if present but not in applied state
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_config = ConfigurationManager.get_app_config()
    rook_ceph_name = app_config.get_rook_ceph_app_name()
    base_path = app_config.get_base_application_path()

    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(active_ssh_connection).wait_for_ceph_health_status(expect_health_status=True)

    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    if not app_list_keywords.is_app_present(rook_ceph_name):
        get_logger().log_test_case_step("Upload rook-ceph app.")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(rook_ceph_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{rook_ceph_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

        get_logger().log_test_case_step("Apply rook-ceph app.")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)
    else:
        app_show = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
        app_status = app_show.get_system_application_object().get_status()
        if app_status != "applied":
            get_logger().log_test_case_step("Apply rook-ceph app.")
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)


@mark.p2
@mark.lab_has_rook_ceph
def test_post_upgrade_check_rook_ceph_app():
    """
    Verify ceph health and rook-ceph application status after upgrade, then remove, apply, abort, and re-apply.

    Test Steps:
        - Verify ceph health status is healthy
        - Validate the rook-ceph application is present and in applied state
        - Remove the rook-ceph application using "system application-remove"
        - Apply the rook-ceph application without waiting for completion
        - Abort the rook-ceph application using "system application-abort"
        - Validate the application status changed to apply-failed
        - Apply the rook-ceph application again to ensure it can be applied after aborting
        - Verify ceph health status is healthy
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    rook_ceph_name = ConfigurationManager.get_app_config().get_rook_ceph_app_name()

    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(active_ssh_connection).wait_for_ceph_health_status(expect_health_status=True)

    get_logger().log_test_case_step("Validate rook-ceph app is applied.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(rook_ceph_name, "applied")

    get_logger().log_test_case_step("Remove rook-ceph.")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(rook_ceph_name)
    system_application_remove_input.set_force_removal(True)
    system_application_remove_input.set_timeout_in_seconds(1800)
    system_application_remove_input.set_check_interval_in_seconds(1)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Apply rook-ceph.")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, wait_for_applied=False)

    get_logger().log_test_case_step("Abort rook-ceph.")
    SystemApplicationAbortKeywords(active_ssh_connection).system_application_abort(app_name=rook_ceph_name)

    get_logger().log_test_case_step("Validate application status changed to apply-failed.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(rook_ceph_name, "apply-failed")

    get_logger().log_test_case_step("Apply rook-ceph.")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)

    get_logger().log_test_case_step("Checking ceph health.")
    CephStatusKeywords(active_ssh_connection).wait_for_ceph_health_status(expect_health_status=True)
