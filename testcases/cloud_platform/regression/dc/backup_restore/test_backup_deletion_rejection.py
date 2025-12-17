from typing import List

from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_rejection_invalid_state(request):
    """
    Verify delete backup command gets rejected for remote backup if subcloud is not in a valid state.

    Test Steps:
        - Create a subcloud backup on remote.
        - Run backup command and verify it gets rejected.
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    current_release = CloudPlatformVersionManagerClass().get_sw_version()

    # Path to where the backup file will store.
    local_path = f"/opt/platform-backup/backups/{current_release}/{subcloud_name}_platform_backup_*.tgz"
    central_path = "/opt/dc-vault/backups/"


    def teardown():
        get_logger().log_info("Managing back subcloud")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)
        get_logger().log_info("Removing test files during teardown")
        FileKeywords(central_ssh).delete_folder_with_sudo(central_path)
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(local_path)

    request.addfinalizer(teardown)

    # Create a sbcloud backup
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=local_path, subcloud=subcloud_name, local_only=True, release=str(current_release))

    # Unmanage the subcloud so the backup command is rejected
    # by a subcloud with invalid state.
    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)

    # Attempt to delete the backup created for major release.
    get_logger().log_info(f"Attempt {subcloud_name} backup deletion")
    dc_manager_backup.reject_delete_subcloud_backup(central_ssh, str(current_release), subcloud=subcloud_name, local_only=True, sysadmin_password=subcloud_password)


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_rejection_version_mismatch(request):
    """
    Verify delete backup command gets rejected for central backup if
    software version is different from backup software version.

    Test Steps:
        - Create a subcloud backup on remote.
        - Run backup command and verify it gets rejected.
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    current_release = CloudPlatformVersionManagerClass().get_sw_version()
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    # Path to where the backup file will store.
    central_path = "/opt/dc-vault/backups/"
    local_path = "/opt/platform-backup/backups/"


    def teardown():
        get_logger().log_info("Managing back subcloud")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)
        get_logger().log_info("Removing test files during teardown")
        FileKeywords(central_ssh).delete_folder_with_sudo(central_path)
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(local_path)

    request.addfinalizer(teardown)

    # Create a sbcloud backup
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name, release=str(current_release))

    # Unmanage the subcloud so the backup command is rejected
    # by a subcloud with invalid state.
    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)

    # Attempt to delete the backup created for major release.
    get_logger().log_info(f"Attempt {subcloud_name} backup deletion")
    dc_manager_backup.reject_delete_subcloud_backup(central_ssh, str(current_release), subcloud=subcloud_name, local_only=True, sysadmin_password=subcloud_password)

    # Attempt to delete the backup created for last major release.
    # Command must be rejected even if backup doesn't exist for this release.
    get_logger().log_info(f"Attempt {subcloud_name} backup deletion")
    dc_manager_backup.reject_delete_subcloud_backup(central_ssh, str(last_major_release), subcloud=subcloud_name, local_only=True, sysadmin_password=subcloud_password)
