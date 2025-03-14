import re

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.linux.date.date_keywords import DateKeywords


def test_verify_backup_central(request):
    """

    Verify backup files are stored in centralized archive
    Verify backup date and backup state of single subcloud
    Test Steps:
        - Backup subcloud to store the file on the System Controller
        - Verify the subcloud backup file is transferred to the centralized
    default location
        - Check backup match current Date and if it is complete
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    central_path = f"/opt/dc-vault/backups/{subcloud_name}/{release}"

    def teardown():
        get_logger().log_info("Removing test files during teardown")
        FileKeywords(central_ssh).delete_folder_with_sudo("/opt/dc-vault/backups/")

    request.addfinalizer(teardown)

    # Create a subcloud backup and verify the subcloud backup file in central_path
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)

    get_logger().log_info("Checking Subcloud's backup_status, backup_datetime")
    subcloud_show_object = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()
    backup_status = subcloud_show_object.get_backup_status()
    backup_datetime = subcloud_show_object.get_backup_datetime()

    backup_date = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", backup_datetime)
    current_date = DateKeywords(central_ssh).get_current_date()

    # Verifying that backup has been successfully completed and was created today.
    validate_equals(backup_status, "complete-central", "Verifying that the backup is completed successfully.")
    validate_equals(backup_date[0].strip(), current_date, "Verifying that the backup was created today")


def test_verify_backup_local_custom_path(request):
    """
    Verify backup files are stored locally to custom directory

    Test Steps:
        - Create a YAML file and add backup backup_dir parameter
        - Verify file created on the System Controller
        - Run dcmanager CLI Backup with --local-only --backup-values
        - Verify the backup files are stored locally (subcloud) using
    the configured path.
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

    def teardown():
        get_logger().log_info("Removing test files")
        FileKeywords(central_ssh).delete_folder_with_sudo("subcloud_backup.yaml")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(f"{subcloud_name}_platform_backup_*.tgz")

    request.addfinalizer(teardown)

    get_user = lab_config.get_admin_credentials().get_user_name()
    home_path = f"/home/{get_user}/"

    backup_yaml_path = f"{home_path}subcloud_backup.yaml"
    backup_yaml_cmd = f"echo 'backup_dir: {home_path}' > {backup_yaml_path}"

    get_logger().log_info("Creating the custom yaml to store backup")
    central_ssh.send(backup_yaml_cmd)

    get_logger().log_info("Checking if the yaml was created")
    FileKeywords(central_ssh).file_exists(backup_yaml_path)

    # Create a subcloud backup and verify the subcloud backup file in local custom path.
    get_logger().log_info(f"Create {subcloud_name} backup locally on custom path")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{home_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, backup_yaml=backup_yaml_path)
