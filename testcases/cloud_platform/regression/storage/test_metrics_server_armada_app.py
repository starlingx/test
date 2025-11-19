from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
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


def setup(request, active_ssh_connection):
    """Setup function to ensure metrics-server is applied before tests."""
    app_config = ConfigurationManager.get_app_config()
    metrics_server_name = app_config.get_metric_server_app_name()
    get_logger().log_setup_step("Checking ceph health.")
    ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)
    get_logger().log_setup_step("Check app metrics-server is applied.")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(metrics_server_name, "applied")

    def cleanup():
        if not SystemApplicationListKeywords(active_ssh_connection).is_app_present(metrics_server_name):
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)
        get_logger().log_teardown_step("Checking ceph health.")
        ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
        ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    request.addfinalizer(cleanup)
    return metrics_server_name


@mark.p2
def test_remove_apply_metrics_server_app(request):
    """
    Remove and apply the metrics-server application.
    Test Steps:
        - Run this command "system application-remove metrics-server"
        - The status of the application should change to uploaded
        - Run this command "system application-apply"
        - The metrics-server application was applied
    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)
    get_logger().log_test_case_step("Remove metrics-server")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(metrics_server_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)
    get_logger().log_test_case_step("Apply metrics-server")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)


@mark.p2
def test_rollback_metrics_server_app(request: FixtureRequest):
    """
    Rollback metrics-server application to a previous version.

    Test Steps:
        - Record current version of metrics-server
        - Transfer tarball from local machine to /home/sysadmin
        - Mount /usr with read-write permissions
        - Copy tarball to /usr/local/share/applications/helm/
        - Execute system application-update with tarball filename
        - Verify the metrics-server version has changed (rollback)

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current metrics-server version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    current_version = current_app_info.get_system_application_object().get_version()

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")
        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original metrics-server version")
            # Remove the rolled back version
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(metrics_server_name)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            # Delete the rolled back version
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(metrics_server_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Copy original tarball to base application path")
            FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/metrics-server-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(active_ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

            # Upload original version
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(metrics_server_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            # Apply original version
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)

            # Delete tarball file from /home/sysadmin
            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            FileKeywords(active_ssh_connection).delete_file(f"/home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    # Transfer tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_metrics_server_app_tarball().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(active_ssh_connection).upload_file(app_config.get_metrics_server_app_tarball(), temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(active_ssh_connection).remount_read_write("/usr")

    # Copy metrics-server*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Move metrics-server*.tgz to /home/sysadmin")
    FileKeywords(active_ssh_connection).move_file(f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Move tarball to base application path")
    FileKeywords(active_ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    # Rollback metrics-servers with tarball
    get_logger().log_test_case_step("Rollback metrics-servers with tarball")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(metrics_server_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Verify the application version has changed (rollback)
    get_logger().log_test_case_step("Verify metrics-servers version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")


@mark.p2
def test_update_metrics_server_app(request: FixtureRequest):
    """
    Update metrics-servers application.

    Test Steps:
        - Roll back the metrics-servers
        - Remove tarball from application base path
        - Copy tarball from /home/sysadmin to application base path
        - Check if the application was upgraded

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    metrics_server_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")
        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original metrics-servers version")
            # Remove the rolled back version
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(metrics_server_name)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            # Delete the rolled back version
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(metrics_server_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Copy original tarball to base application path")
            FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/metrics-server-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            FileKeywords(active_ssh_connection).move_file(app_config.get_base_application_path() + tarball_filename, "/home/sysadmin/", sudo=True)

            # Upload original version
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(metrics_server_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            # Apply original version
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=metrics_server_name)

            # Delete tarball file from /home/sysadmin
            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            FileKeywords(active_ssh_connection).delete_file(f"/home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current metrics-servers version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    current_version = current_app_info.get_system_application_object().get_version()

    # Transfer tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    tarball_filename = app_config.get_metrics_server_app_tarball().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"
    FileKeywords(active_ssh_connection).upload_file(app_config.get_metrics_server_app_tarball(), temp_remote_path)

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    MountKeywords(active_ssh_connection).remount_read_write("/usr")

    # Copy metrics-server*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Move metrics-server*.tgz to /home/sysadmin")
    FileKeywords(active_ssh_connection).move_file(f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz", "/home/sysadmin/", sudo=True)

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Move tarball to base application path")
    FileKeywords(active_ssh_connection).move_file(temp_remote_path, app_config.get_base_application_path(), sudo=True)

    # Rollback metrics-servers with tarball
    get_logger().log_test_case_step("Rollback metrics-servers with tarball")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(metrics_server_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Verify the application version has changed (rollback)
    get_logger().log_test_case_step("Verify metrics-servers version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")

    # Remove tarball from application base path
    get_logger().log_test_case_step("Remove tarball from application base path")
    FileKeywords(active_ssh_connection).delete_file(f"{app_config.get_base_application_path()}{tarball_filename}")

    # Move tarball from /home/sysadmin to base application path
    get_logger().log_test_case_step("Copy tarball from /home/sysadmin to base application path")
    FileKeywords(active_ssh_connection).move_file(f"/home/sysadmin/metrics-server-{current_version}.tgz", app_config.get_base_application_path(), sudo=True)

    # Update metrics-servers with new tarball
    get_logger().log_test_case_step("Update metrics-servers with new tarball")
    upgrade_tarball_path = f"{app_config.get_base_application_path()}metrics-server-{current_version}.tgz"
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(metrics_server_name)
    system_application_update_input.set_tar_file_path(upgrade_tarball_path)
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Check if the application was upgraded
    get_logger().log_test_case_step("Check if the application was upgraded")
    upgraded_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(metrics_server_name)
    upgraded_version = upgraded_app_info.get_system_application_object().get_version()
    validate_equals(upgraded_version, current_version, "Application version should match original version after upgrade")
    get_logger().log_info(f"Application status after upgrade: {upgraded_app_info.get_system_application_object()}")
