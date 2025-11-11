from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.secure_transfer_file.secure_transfer_file import SecureTransferFile
from framework.ssh.secure_transfer_file.secure_transfer_file_enum import TransferDirection
from framework.ssh.secure_transfer_file.secure_transfer_file_input_object import SecureTransferFileInputObject
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


@mark.p2
def test_rollback_platform_integ_app(request: FixtureRequest):
    """
    Rollback platform-integ-apps application to a previous version.

    Test Steps:
        - Record current version of platform-integ-apps
        - Transfer tarball from local machine to /home/sysadmin
        - Mount /usr with read-write permissions
        - Copy tarball to /usr/local/share/applications/helm/
        - Execute system application-update with tarball filename
        - Verify the platform-integ-apps version has changed (rollback)

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    platform_integ_apps_name = setup(request, active_ssh_connection)

    # Record current version before rollback
    get_logger().log_test_case_step("Record current platform-integ-apps version")
    current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
    current_version = current_app_info.get_system_application_object().get_version()

    def teardown():
        get_logger().log_teardown_step("Test- Teardown: Check if restore needed")
        # Check current version on system
        current_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
        system_version = current_app_info.get_system_application_object().get_version()

        if system_version != current_version:
            get_logger().log_teardown_step("Restoring original platform-integ-apps version")
            # Remove the rolled back version
            system_application_remove_input = SystemApplicationRemoveInput()
            system_application_remove_input.set_app_name(platform_integ_apps_name)
            SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

            # Delete the rolled back version
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(platform_integ_apps_name)
            SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)

            # Copy original tarball from /home/sysadmin to base_application_path
            get_logger().log_teardown_step("Copy original tarball to base application path")
            active_ssh_connection.send_as_sudo(f"mv /home/sysadmin/platform-integ-app*.tgz {app_config.get_base_application_path()}")

            # Move rollback tarball from base_application_path to /home/sysadmin
            get_logger().log_teardown_step("Move rollback tarball to /home/sysadmin")
            active_ssh_connection.send_as_sudo(f"mv {app_config.get_base_application_path()}{tarball_filename} /home/sysadmin/")

            # Upload original version
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(platform_integ_apps_name)
            system_application_upload_input.set_tar_file_path(f"{app_config.get_base_application_path()}platform-integ-app*.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

            # Apply original version
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=platform_integ_apps_name)

            # Delete tarball file from /home/sysadmin
            get_logger().log_teardown_step("Delete tarball file from /home/sysadmin")
            active_ssh_connection.send_as_sudo(f"rm -f /home/sysadmin/{tarball_filename}")
        else:
            get_logger().log_teardown_step("No restore needed - version unchanged")

    request.addfinalizer(teardown)

    # Transfer tarball from local machine to /home/sysadmin
    get_logger().log_test_case_step("Transfer rollback tarball from local machine to /home/sysadmin")
    app_config = ConfigurationManager.get_app_config()
    local_path = get_stx_resource_path(app_config.get_base_application_localhost())
    tarball_filename = app_config.get_base_application_localhost().split("/")[-1]
    temp_remote_path = f"/home/sysadmin/{tarball_filename}"

    sftp_client = active_ssh_connection.get_sftp_client()
    transfer_input = SecureTransferFileInputObject()
    transfer_input.set_sftp_client(sftp_client)
    transfer_input.set_origin_path(local_path)
    transfer_input.set_destination_path(temp_remote_path)
    transfer_input.set_transfer_direction(TransferDirection.FROM_LOCAL_TO_REMOTE)
    transfer_input.set_force(True)

    SecureTransferFile(transfer_input).transfer_file()

    # Mount /usr to be able to write the tarball
    get_logger().log_test_case_step("Mount /usr with read-write permissions")
    active_ssh_connection.send_as_sudo("mount -o rw,remount /usr")

    # Copy platform_integ_app*.tgz from base_application_path to /home/sysadmin
    get_logger().log_test_case_step("Move platform_integ_app*.tgz to /home/sysadmin")
    active_ssh_connection.send_as_sudo(f"mv {app_config.get_base_application_path()}platform-integ-app*.tgz /home/sysadmin/")

    # Copy tarball from /home/sysadmin to base_application_path
    get_logger().log_test_case_step("Move tarball to base application path")
    active_ssh_connection.send_as_sudo(f"mv {temp_remote_path} {app_config.get_base_application_path()}")

    # Rollback platform-integ-apps with tarball
    get_logger().log_test_case_step("Rollback platform-integ-apps with tarball")
    system_application_update_input = SystemApplicationUpdateInput()
    system_application_update_input.set_app_name(platform_integ_apps_name)
    system_application_update_input.set_tar_file_path(f"{app_config.get_base_application_path()}{tarball_filename}")
    SystemApplicationUpdateKeywords(active_ssh_connection).system_application_update(system_application_update_input)

    # Verify the application version has changed (rollback)
    get_logger().log_test_case_step("Verify platform-integ-apps version has changed after rollback")
    rollback_app_info = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(platform_integ_apps_name)
    rollback_version = rollback_app_info.get_system_application_object().get_version()
    validate_not_equals(current_version, rollback_version, "Application version should have changed after rollback")
