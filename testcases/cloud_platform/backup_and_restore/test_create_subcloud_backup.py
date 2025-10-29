from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords


@mark.p2
@mark.lab_has_subcloud
def test_central_backup_standard_subcloud_inactive_load(request):
    """
    Verify central backup restore on an already deployed subcloud with n-1 release.

    Test Steps:
        - Create a central subcloud backup for n-1 release.
        - Verify the central backup completion status.

    Teardown:
        - Remove files created while the TC was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_release = CloudPlatformVersionManagerClass().get_last_major_release()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_managed_subcloud = dcmanager_subcloud_list_keywords.get_healthy_subcloud_by_type_and_release(LabTypeEnum.STANDARD.value, version=str(subcloud_release))
    subcloud_name = lowest_managed_subcloud.get_name()

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Get subcloud credentials for backup operations
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Setup central backup path and teardown
    central_path = "/opt/dc-vault/backups/"

    def teardown():
        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(central_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on central cloud
    get_logger().log_info(f"Create {subcloud_name} backup on central cloud.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}/{subcloud_name}/{subcloud_release}", subcloud=subcloud_name)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")


@mark.p2
@mark.lab_has_subcloud
def test_local_backup_standard_subcloud_inactive_load(request):
    """
    Verify local backup restore on an already deployed subcloud with n-1 release.

    Test Steps:
        - Create a local subcloud backup for n-1 release.
        - Verify the local backup completion status.

    Teardown:
        - Remove files created while the TC was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_last_major_release()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    standard_subcloud = dcmanager_subcloud_list_keywords.get_healthy_subcloud_by_type_and_release(LabTypeEnum.STANDARD.value, version=str(release))
    subcloud_name = standard_subcloud.get_name()

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Get subcloud credentials for backup operations
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Setup local backup path and teardown
    local_path = f"/opt/platform-backup/backups/{release}/{subcloud_name}_platform_backup_*.tgz"

    def teardown_backup():
        get_logger().log_info("Cleaning up backup files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo("/opt/platform-backup/backups/")

    request.addfinalizer(teardown_backup)

    # Create local backup on rehomed subcloud
    get_logger().log_info(f"Creating local backup on rehomed subcloud {subcloud_name}")
    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=local_path, subcloud=subcloud_name, local_only=True)

    # Wait for local backup completion
    get_logger().log_info("Waiting for local backup creation to complete")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")
