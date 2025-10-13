from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords


@mark.p2
@mark.lab_has_subcloud
def test_restore_remote_backup_active_load(request):
    """
    Verify remote backup restore on an already deployed host. Parameter --with-install
    must be set since the subcloud is already deployed.

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Restore the subcloud local backup
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_managed_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_managed_subcloud.get_name()

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on local_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    local_path = f"/opt/platform-backup/backups/{release}/{subcloud_name}_platform_backup_*.tgz"

    def teardown():
        get_logger().log_info(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name,10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo("/opt/platform-backup/backups/")

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on local")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=local_path, subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, local_only=True, with_install=True)

@mark.p2
@mark.lab_has_subcloud
def test_restore_central_backup_inactive_load(request):
    """
    Verify central stored backup restore on an already deployed host with an inactive
    load. Parameter --with-install must be set since the subcloud is already deployed.

    Test Steps:
        - Deploy a subcloud with n-1 release.
        - Create a Subcloud backup and check it on central path
        - Restore the subcloud from the central backup
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_release = CloudPlatformVersionManagerClass().get_last_major_release()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_managed_subcloud = dcmanager_subcloud_list_keywords.get_one_subcloud_by_release(str(subcloud_release))
    subcloud_name = lowest_managed_subcloud.get_name()

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    central_path = "/opt/dc-vault/backups/"

    def teardown():
        get_logger().log_info(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name,10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(central_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on central cloud.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}/{subcloud_name}/{subcloud_release}", subcloud=subcloud_name)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name,  expected_status="complete-central")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(subcloud_release))

@mark.p2
@mark.lab_has_subcloud
def test_restore_remote_backup_inactive_load(request):
    """
    Verify remote stored backup restore on an already deployed host with an inactive
    load. Parameter --with-install must be set since the subcloud is already deployed.

    Test Steps:
        - Deploy a subcloud with n-1 load.
        - Create a Subcloud backup and check it on remote path
        - Restore the subcloud from the central backup
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_release = CloudPlatformVersionManagerClass().get_last_major_release()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_managed_subcloud = dcmanager_subcloud_list_keywords.get_one_subcloud_by_release(str(subcloud_release))
    subcloud_name = lowest_managed_subcloud.get_name()

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    local_path = f"/opt/platform-backup/backups/{subcloud_release}"

    def teardown():
        get_logger().log_info(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name,10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(local_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on local")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=local_path, subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, local_only=True, release=str(subcloud_release))
