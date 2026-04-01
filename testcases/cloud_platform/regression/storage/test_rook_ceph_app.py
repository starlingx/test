from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.object.system_application_update_input import SystemApplicationUpdateInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.application.system_application_update_keywords import SystemApplicationUpdateKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.mount.mount_keywords import MountKeywords

ROOK_CEPH_APP_NAME = "rook-ceph"


def setup(request: FixtureRequest, active_ssh_connection: SSHConnection) -> str:
    """Setup function to ensure rook-ceph is applied before tests.

    Records the initial application state and restores it during cleanup.

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown.
        active_ssh_connection (SSHConnection): active SSH connection to the controller.

    Returns:
        str: the rook-ceph application name.
    """
    app_config = ConfigurationManager.get_app_config()
    rook_ceph_name = app_config.get_rook_ceph_app_name()
    base_path = app_config.get_base_application_path()

    get_logger().log_setup_step("Checking ceph health.")
    ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)

    # Record initial state before any setup modifications.
    initial_present = app_list_keywords.is_app_present(rook_ceph_name)
    initial_status = None
    if initial_present:
        app_show = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
        initial_status = app_show.get_system_application_object().get_status()
        get_logger().log_setup_step(f"Initial rook-ceph state: {initial_status}")
    else:
        get_logger().log_setup_step("Initial rook-ceph state: not present, Upload rook-ceph app.")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(rook_ceph_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{rook_ceph_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

    app_show = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
    app_status = app_show.get_system_application_object().get_status()
    if app_status != "applied":
        get_logger().log_setup_step("Apply rook-ceph app.")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)

    def cleanup():
        get_logger().log_teardown_step("Restoring rook-ceph to applied state")
        current_status = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name).get_system_application_object().get_status()

        if current_status != "applied":
            SystemApplicationRemoveKeywords(active_ssh_connection).cleanup_app_if_present(rook_ceph_name, force_removal=True, timeout_in_seconds=1800, check_interval_in_seconds=1)
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)

        get_logger().log_teardown_step("Checking ceph health.")
        ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    request.addfinalizer(cleanup)
    return rook_ceph_name


@mark.p2
@mark.lab_has_rook_ceph
def test_remove_apply_rook_ceph_app(request: FixtureRequest):
    """
    Remove and apply the rook-ceph application.

    Test Steps:
        - Run this command "system application-remove rook-ceph"
        - The status of the application should change to uploaded
        - Run this command "system application-apply"
        - The rook-ceph application was applied

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    rook_ceph_name = setup(request, active_ssh_connection)
    get_logger().log_test_case_step("Remove rook-ceph")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(rook_ceph_name)
    system_application_remove_input.set_force_removal(True)
    system_application_remove_input.set_timeout_in_seconds(1800)
    system_application_remove_input.set_check_interval_in_seconds(1)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Apply rook-ceph")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)


@mark.p2
@mark.lab_has_rook_ceph
def test_delete_rook_ceph_app(request: FixtureRequest):
    """
    Delete rook-ceph application.

    Test Steps:
        - Run this command "system application-remove rook-ceph"
        - The status of the application should change to uploaded
        - Run this command "system application-delete"
        - The rook-ceph application was deleted
        - Verify the application is no longer present in the application list

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    rook_ceph_name = setup(request, active_ssh_connection)
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")
        if not SystemApplicationListKeywords(active_ssh_connection).is_app_present(rook_ceph_name):
            get_logger().log_teardown_step("App not present, uploading rook-ceph")
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(rook_ceph_name)
            system_application_upload_input.set_tar_file_path(f"{base_path}{rook_ceph_name}*.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)
            get_logger().log_teardown_step("Apply rook-ceph app")
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Remove rook-ceph")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(rook_ceph_name)
    system_application_remove_input.set_force_removal(True)
    system_application_remove_input.set_timeout_in_seconds(1800)
    system_application_remove_input.set_check_interval_in_seconds(1)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Delete rook-ceph")
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(rook_ceph_name)
    app_delete_response = SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(app_delete_response.rstrip(), "Application rook-ceph deleted.", "Application deletion.")

    get_logger().log_test_case_step("Verify rook-ceph is no longer present in application list")
    is_present = SystemApplicationListKeywords(active_ssh_connection).is_app_present(rook_ceph_name)
    validate_equals(is_present, False, "Application should not be present after deletion.")


@mark.p2
@mark.lab_has_rook_ceph
def test_rollback_rook_ceph_app(request: FixtureRequest):
    """
    Rollback rook-ceph application to a previous version.

    Test Steps:
        - Record current version of rook-ceph
        - Transfer tarball from local machine to /home/sysadmin
        - Mount /usr with read-write permissions
        - Copy tarball to /usr/local/share/applications/helm/
        - Execute system application-update with tarball filename
        - Verify the rook-ceph version has changed (rollback)

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    rook_ceph_name = setup(request, active_ssh_connection)

    get_logger().log_test_case_step("Record current rook-ceph version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
    current_version = current_app_info.get_system_application_object().get_version()

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original rook-ceph version")
            get_logger().log_test_case_step("Remove rook-ceph")
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(rook_ceph_name)
            system_application_remove_input.set_force_removal(True)
            system_application_remove_input.set_timeout_in_seconds(1800)
            system_application_remove_input.set_check_interval_in_seconds(1)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
            get_logger().log_test_case_step("Delete rook-ceph")
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(rook_ceph_name)
            app_delete_response = SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)
            validate_equals(app_delete_response.rstrip(), "Application rook-ceph deleted.", "Application deletion.")

            get_logger().log_teardown_step("Copy original tarball to base application path")
            FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/rook-ceph-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(active_ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(rook_ceph_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}rook-ceph-{current_version}.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)

            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            FileKeywords(active_ssh_connection).delete_file(f"/home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_rook_ceph_app_tarball().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(active_ssh_connection).upload_file(app_config.get_rook_ceph_app_tarball(), temp_remote_path)

    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(active_ssh_connection).remount_read_write("/usr")

    get_logger().log_test_case_step("Move rook-ceph*.tgz to /home/sysadmin")
    FileKeywords(active_ssh_connection).move_file(f"{app_config.get_base_application_path()}rook-ceph-{current_version}.tgz", "/home/sysadmin/", sudo=True)

    get_logger().log_test_case_step("Move tarball to base application path")
    FileKeywords(active_ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    get_logger().log_test_case_step("Check if application update is already in progress")
    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    app_status = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name).get_system_application_object().get_status()
    if app_status == SystemApplicationStatusEnum.UPDATING.value:
        get_logger().log_info("Application update already in progress. Waiting for it to complete.")
        app_list_keywords.validate_app_status(rook_ceph_name, SystemApplicationStatusEnum.APPLIED.value, 1800, 5)
    else:
        get_logger().log_test_case_step("Rollback rook-ceph with tarball")
        system_application_update_input = SystemApplicationUpdateInput()
        system_application_update_input.set_app_name(rook_ceph_name)
        system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
        system_application_update_input.set_timeout_in_seconds(1800)
        SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    get_logger().log_test_case_step("Verify rook-ceph version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")


@mark.p2
@mark.lab_has_rook_ceph
def test_update_rook_ceph_app(request: FixtureRequest):
    """
    Update rook-ceph application.

    Test Steps:
        - Roll back the rook-ceph
        - Remove tarball from application base path
        - Copy tarball from /home/sysadmin to application base path
        - Check if the application was upgraded

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    rook_ceph_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original rook-ceph version")
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(rook_ceph_name)
            system_application_remove_input.set_force_removal(True)
            system_application_remove_input.set_timeout_in_seconds(1800)
            system_application_remove_input.set_check_interval_in_seconds(1)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(rook_ceph_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

            get_logger().log_teardown_step("Copy original tarball to base application path")
            FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/rook-ceph-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(active_ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(rook_ceph_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}rook-ceph-{current_version}.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=rook_ceph_name, timeout=1800)

            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            FileKeywords(active_ssh_connection).delete_file(f"/home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Record current rook-ceph version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
    current_version = current_app_info.get_system_application_object().get_version()

    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_rook_ceph_app_tarball().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(active_ssh_connection).upload_file(app_config.get_rook_ceph_app_tarball(), temp_remote_path)

    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(active_ssh_connection).remount_read_write("/usr")

    get_logger().log_test_case_step("Move rook-ceph*.tgz to /home/sysadmin")
    FileKeywords(active_ssh_connection).move_file(f"{app_config.get_base_application_path()}rook-ceph-{current_version}.tgz", "/home/sysadmin/", sudo=True)

    get_logger().log_test_case_step("Move tarball to base application path")
    FileKeywords(active_ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    get_logger().log_test_case_step("Check if application update is already in progress")
    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)
    app_status = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name).get_system_application_object().get_status()
    if app_status == SystemApplicationStatusEnum.UPDATING.value:
        get_logger().log_info("Application update already in progress. Waiting for it to complete.")
        app_list_keywords.validate_app_status(rook_ceph_name, SystemApplicationStatusEnum.APPLIED.value, 1800, 5)
    else:
        get_logger().log_test_case_step("Rollback rook-ceph with tarball")
        system_application_update_input = SystemApplicationUpdateInput()
        system_application_update_input.set_app_name(rook_ceph_name)
        system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
        system_application_update_input.set_timeout_in_seconds(1800)
        SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    get_logger().log_test_case_step("Verify rook-ceph version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")

    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(active_ssh_connection).delete_file(f"{app_config.get_base_application_path()}{tarball_filename}")

    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to base application path")
    FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/rook-ceph-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

    get_logger().log_test_case_step("Check if application update is already in progress before upgrade")
    app_status = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name).get_system_application_object().get_status()
    if app_status == SystemApplicationStatusEnum.UPDATING.value:
        get_logger().log_info("Application update already in progress. Waiting for it to complete.")
        app_list_keywords.validate_app_status(rook_ceph_name, SystemApplicationStatusEnum.APPLIED.value, 1800, 5)
    else:
        get_logger().log_test_case_step("Update rook-ceph with new tarball")
        upgrade_tarball_path = f"{app_config.get_base_application_path()}rook-ceph-{current_version}.tgz"
        system_application_update_input = SystemApplicationUpdateInput()
        system_application_update_input.set_app_name(rook_ceph_name)
        system_application_update_input.set_tar_file_path(upgrade_tarball_path)
        system_application_update_input.set_timeout_in_seconds(1800)
        SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    get_logger().log_test_case_step("Check if the application was upgraded")
    upgraded_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(rook_ceph_name)
    upgraded_version = upgraded_app_info.get_system_application_object().get_version()
    validate_equals(upgraded_version, current_version, "Application version should match original version after upgrade")
    get_logger().log_info(f"Application status after upgrade: {upgraded_app_info.get_system_application_object()}")
