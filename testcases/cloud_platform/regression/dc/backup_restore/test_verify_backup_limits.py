from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords


@mark.p2
@mark.lab_has_subcloud
def test_verify_one_release_per_subcloud_on_central(request):
    """Verify only one release per subcloud on Central path

    Test Steps:
        - Create a Subcloud backup and check it on Central path
        - Create a Second Subcloud backup and check it on Central path
        - Verify that the new backup replace the old one checking timestamp
    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()

    validate_subcloud_health(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    central_path = "/opt/dc-vault/backups"
    subcloud_backup_path = f"{central_path}/{subcloud_name}/{release}"

    dcmanager_subcloud_obj = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()

    if FileKeywords(central_ssh).validate_file_exists_with_sudo(central_path):
        get_logger().log_info("Removing test files.")
        FileKeywords(central_ssh).delete_folder_with_sudo(central_path)

    # Create a sbcloud backup
    # First creation backup
    get_logger().log_info(f"Create first {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)

    get_logger().log_info("Checking if first backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    get_logger().log_info(f"First {subcloud_name} backup created at {subcloud_backup_path}.")
    first_backup_datetime = dcmanager_subcloud_obj.get_backup_datetime()

    # Removes previously created backup files, avoiding a false 'backup completed' flag.
    get_logger().log_info("Removing test files.")
    FileKeywords(central_ssh).delete_folder_with_sudo(central_path)

    # Second backup creation
    validate_subcloud_health(subcloud_name)
    get_logger().log_info(f"Create second {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)

    get_logger().log_info("Checking if second backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    dcmanager_subcloud_obj = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()

    second_backup_datetime = dcmanager_subcloud_obj.get_backup_datetime()

    validate_not_equals(second_backup_datetime, first_backup_datetime, "The backup created time has changed.")


@mark.p2
@mark.lab_has_subcloud
def test_verify_two_releases_per_subcloud_on_central(request):
    """Verify only two releases per subcloud on Central path

    Test Steps:
        - Create a Subcloud backup and check it on Central path
        - Change the backup's name to 24.03
        - Create a Second Subcloud backup and check it on Central path
        - Change the backup's name to 24.09
        - Create a Third Subcloud backup and check it on Central path
        - Verify that only the latest two releases backups per subcloud exists

    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()

    validate_subcloud_health(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    central_path = "/opt/dc-vault/backups"

    old_release_1 = CloudPlatformVersionManagerClass().get_last_major_release().get_name()
    old_release_2 = CloudPlatformVersionManagerClass().get_second_last_major_release().get_name()

    release_central_path = f"{central_path}/{subcloud_name}/{release}"
    old_release_1_central_path = f"{central_path}/{subcloud_name}/{old_release_1}"
    old_release_2_central_path = f"{central_path}/{subcloud_name}/{old_release_2}"

    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")

    if FileKeywords(central_ssh).validate_file_exists_with_sudo(release_central_path):
        get_logger().log_info("Removing test files.")
        FileKeywords(central_ssh).delete_folder_with_sudo(release_central_path)

    if FileKeywords(central_ssh).validate_file_exists_with_sudo(old_release_1_central_path):
        get_logger().log_info("Removing test files.")
        FileKeywords(central_ssh).delete_folder_with_sudo(old_release_1_central_path)

    if FileKeywords(central_ssh).validate_file_exists_with_sudo(old_release_2_central_path):
        get_logger().log_info("Removing test files.")
        FileKeywords(central_ssh).delete_folder_with_sudo(old_release_2_central_path)

    # First subcloud backup creation
    get_logger().log_info(f"Create first {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)
    get_logger().log_info("Checking if first backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    get_logger().log_info(f"Changing backup name to {old_release_1}")
    FileKeywords(central_ssh).rename_file(release_central_path, old_release_1_central_path)

    # Second subcloud backup creation
    validate_subcloud_health(subcloud_name)
    get_logger().log_info(f"Create a second {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)
    get_logger().log_info("Checking if second backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    get_logger().log_info(f"Changing backup name to {old_release_2}")
    FileKeywords(central_ssh).rename_file(release_central_path, old_release_2_central_path)

    # Third backup creation
    validate_subcloud_health(subcloud_name)
    get_logger().log_info(f"Create a third {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)
    get_logger().log_info("Checking if third backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    get_logger().log_info(f"Checking if {old_release_1} backup exists and {old_release_2}" "was deleted")
    old_release_1_exists = FileKeywords(central_ssh).validate_file_exists_with_sudo(old_release_1_central_path)
    old_release_2_exists = FileKeywords(central_ssh).validate_file_exists_with_sudo(old_release_2_central_path)

    validate_equals(old_release_1_exists, True, f"Release {old_release_1} exists")
    validate_equals(old_release_2_exists, False, f"Release {old_release_2} has been deleted.")


@mark.p2
@mark.lab_has_subcloud
def test_verify_one_release_per_subcloud_on_local(request):
    """Verify only one release per subcloud on local path

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Create a Second Subcloud backup and check it on local path
        - Verify that the new backup replace the old one checking timestamp
    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    validate_subcloud_health(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path where backup file will be stored.
    local_path = "/opt/platform-backup/backups"
    local_path_release = f"{local_path}/{release}"

    if FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(local_path_release):
        get_logger().log_info("Removing test files.")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(local_path_release)

    # First creation backup
    # Create a sbcloud backup
    get_logger().log_info(f"Create first backup on {subcloud_name}")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}/{release}/", subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    first_backup_datetime = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_backup_datetime()

    # Second backup creation
    validate_subcloud_health(subcloud_name)
    get_logger().log_info(f"Create second backup on {subcloud_name}")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=local_path, subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if second backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    second_backup_datetime = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_backup_datetime()

    validate_not_equals(second_backup_datetime, first_backup_datetime, "The backup created time has changed.")


@mark.p2
@mark.lab_has_subcloud
def test_verify_two_releases_per_subcloud_on_local(request):
    """Verify only two latest backup releases per subcloud are kept with local-only

    Test Steps:
        - Create a Subcloud backup and check it
        - Change the backup's name to 24.03
        - Create a Second Subcloud backup and check it
        - Change the backup's name to 24.09
        - Create a Third Subcloud backup and check it
        - Verify that the only backups kept are the latest versions backup

    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path where backup file will be stored.
    local_path = "/opt/platform-backup/backups"

    old_release_1 = CloudPlatformVersionManagerClass().get_last_major_release().get_name()
    old_release_2 = CloudPlatformVersionManagerClass().get_second_last_major_release().get_name()

    release_local_path = f"{local_path}/{release}"
    old_release_1_local_path = f"{local_path}/{old_release_1}"
    old_release_2_local_path = f"{local_path}/{old_release_2}"

    if FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(release_local_path):
        get_logger().log_info("Removing test files.")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(local_path)

    if FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(old_release_1_local_path):
        get_logger().log_info("Removing test files.")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(old_release_1_local_path)

    if FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(old_release_2_local_path):
        get_logger().log_info("Removing test files.")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(old_release_2_local_path)

    # First subcloud backup creation
    get_logger().log_info(f"Create first {subcloud_name} backup on local.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}/{release}", subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if first backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    get_logger().log_info(f"Changing backup name to {old_release_1}")
    FileKeywords(subcloud_ssh).rename_file(release_local_path, old_release_1_local_path)

    # Second subcloud backup creation
    get_logger().log_info(f"Create a second {subcloud_name} backup on local.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}/{release}", subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if second backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    get_logger().log_info(f"Changing backup name to {old_release_2}")
    FileKeywords(central_ssh).rename_file(release_local_path, old_release_2_local_path)

    # Third backup creation
    get_logger().log_info(f"Create a third {subcloud_name} backup on local.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}/{release}", subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if third backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    get_logger().log_info(f"Checking if {old_release_1} backup exists and {old_release_2}" "was deleted")
    old_release_1_exists = FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(old_release_1_local_path)
    old_release_2_exists = FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(old_release_2_local_path)

    validate_equals(old_release_1_exists, True, f"Release {old_release_1} exists")
    validate_equals(old_release_2_exists, False, f"Release {old_release_2} has been deleted.")


def validate_subcloud_health(subcloud_name):
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health