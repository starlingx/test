from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords

@mark.p2
@mark.lab_has_subcloud
def test_verify_backup_on_central_inactive_load(request):
    """Verify subcloud with inactive load backup on central

    Test Steps:
        - Create a Subcloud backup and check it on Central path
        - Check if the backup was created successfully.
    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_lower_id_async_subcloud()
    subcloud_name = lowest_subcloud.get_name()
    release = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    validate_subcloud_health(subcloud_name)

    def teardown():
        teardown_central(central_path)

    request.addfinalizer(teardown)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    central_path = "/opt/dc-vault/backups"

    if FileKeywords(central_ssh).validate_file_exists_with_sudo(central_path):
        get_logger().log_info("Removing test files.")
        FileKeywords(central_ssh).delete_folder_with_sudo(central_path)

    # Create a sbcloud backup
    # First creation backup
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)

    get_logger().log_info("Checking if inactive load backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    FileKeywords(central_ssh).validate_file_exists_with_sudo(f"{central_path}/{subcloud_name}/{release}")

@mark.p2
@mark.lab_has_subcloud
def test_verify_backup_local_inactive_load(request):
    """Verify subcloud with inactive load backup on local

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Check if the backup was created successfully.
    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_lower_id_async_subcloud()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    release = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    validate_subcloud_health(subcloud_name)

    def teardown():
        teardown_local(subcloud_name, local_path=local_path_release)

    request.addfinalizer(teardown)

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

    FileKeywords(central_ssh).validate_file_exists_with_sudo(f"{local_path}/{release}")


def validate_subcloud_health(subcloud_name):
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

def teardown_central(backup_path: str):
    """Teardown function for central backup.

    Args:
        backup_path (str): central backup path
    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    # Path to where the backup file will store.
    get_logger().log_info("Removing test files during teardown")
    FileKeywords(central_ssh).delete_folder_with_sudo(backup_path)


def teardown_local(subcloud_name: str, local_path: str):
    """Teardown function for local backup.

    Args:
        subcloud_name (str): subcloud name
        local_path (str): local backup path
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    get_logger().log_info("Removing test files")
    FileKeywords(central_ssh).delete_file("subcloud_backup.yaml")
    FileKeywords(subcloud_ssh).delete_file(f"{local_path}/{subcloud_name}_platform_backup_*.tgz")
