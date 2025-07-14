import re

from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.linux.date.date_keywords import DateKeywords

BACKUP_PATH = "/opt/dc-vault/backups/"


def verify_backup_central(subcloud_name: str):
    """Function to central Backup of a subcloud

    Verify backup files are stored in centralized archive
    Verify backup date and backup state of single subcloud

    Args:
        subcloud_name (str): subcloud name to backup
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()
    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    # Path to where the backup file will store.
    central_path = f"{BACKUP_PATH}{subcloud_name}/{release}"
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


def teardown_central():
    """Teardown function for central backup."""

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    # Path to where the backup file will store.
    get_logger().log_info("Removing test files during teardown")
    FileKeywords(central_ssh).delete_folder_with_sudo(BACKUP_PATH)


def teardown_local(subcloud_name: str):
    """Teardown function for local backup.

    Args:
        subcloud_name (str): subcloud name
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    get_logger().log_info("Removing test files")
    FileKeywords(central_ssh).delete_folder_with_sudo("subcloud_backup.yaml")
    FileKeywords(subcloud_ssh).delete_folder_with_sudo(f"{subcloud_name}_platform_backup_*.tgz")


def verify_backup_local_custom_path(subcloud_name: str):
    """Verify backup files are stored locally to custom directory

    Args:
        subcloud_name (str): subcloud name to backup
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

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


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_central_simplex(request):
    """Central Backup of a subcloud Simplex

    Test Steps:
        - Backup subcloud to store the file on the System Controller
        - Verify the subcloud backup file is transferred to the centralized
    default location
        - Check backup match current Date and if it is complete
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_by_type(LabTypeEnum.SIMPLEX.value)
    request.addfinalizer(teardown_central)
    verify_backup_central(subcloud.get_name())


@mark.p0
@mark.subcloud_lab_is_duplex
def test_verify_backup_central_duplex(request):
    """Central Backup of a subcloud Duplex

    Test Steps:
        - Backup subcloud to store the file on the System Controller
        - Verify the subcloud backup file is transferred to the centralized
    default location
        - Check backup match current Date and if it is complete
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_by_type(LabTypeEnum.DUPLEX.value)
    request.addfinalizer(teardown_central)
    verify_backup_central(subcloud.get_name())


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_simplex(request):
    """

    Test Steps:
        - Create a YAML file and add backup backup_dir parameter
        - Verify file created on the System Controller
        - Run dcmanager CLI Backup with --local-only --backup-values
        - Verify the backup files are stored locally (subcloud) using
    the configured path.
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_by_type(LabTypeEnum.SIMPLEX.value)

    def teardown():
        teardown_local(subcloud.get_name())

    request.addfinalizer(teardown)
    verify_backup_local_custom_path(subcloud.get_name())


@mark.p0
@mark.subcloud_lab_is_duplex
def test_verify_backup_local_duplex(request):
    """

    Test Steps:
        - Create a YAML file and add backup backup_dir parameter
        - Verify file created on the System Controller
        - Run dcmanager CLI Backup with --local-only --backup-values
        - Verify the backup files are stored locally (subcloud) using
    the configured path.
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_by_type(LabTypeEnum.DUPLEX.value)

    def teardown():
        teardown_local(subcloud.get_name())

    request.addfinalizer(teardown)
    verify_backup_local_custom_path(subcloud.get_name())

@mark.lab_has_subcloud
def test_verify_backup_central_simplex_group(request):
    """
    Verify backup of subcloud group

    Test Steps:
        - Create a Subcloud group
        - Assign subcloud to group
        - Verify the subcloud backup file is transferred to the centralized
    default location
        - Check backup match current Date and if it is complete
    Teardown:
        - Remove Test Group
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
    central_path = f"/opt/dc-vault/backups/{subcloud_name}/{release}/"

    def teardown():
        get_logger().log_info("Removing test files")
        FileKeywords(central_ssh).delete_folder_with_sudo("subcloud_backup.yaml")
        FileKeywords(central_ssh).delete_folder_with_sudo(f"{central_path}{subcloud_name}_platform_backup_*.tgz")

    def teardown_group():
        get_logger().log_info("Removing the created subcloud group before teardown.")
        DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud_name=subcloud_name, update_attr="group", update_value="Default")
        DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_delete("TestGroup")

    request.addfinalizer(teardown)
    request.addfinalizer(teardown_group)

    # Create subcloud group TestGroup
    DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_add(group_name="TestGroup")
    # Adds subcloud to TestGroup
    DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud_name=subcloud_name, update_attr="group", update_value="TestGroup")

    group_list = DcmanagerSubcloudGroupKeywords(central_ssh).get_dcmanager_subcloud_group_list_subclouds("TestGroup").get_dcmanager_subcloud_group_list_subclouds()
    subclouds = [subcloud.get_name() for subcloud in group_list]
    validate_list_contains(subcloud_name, subclouds, "Verifies if the subcloud name is in the list of subclouds.")

    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}{subcloud_name}_platform_backup_*.tgz", group="TestGroup", subcloud_list=[subcloud_name], release=str(release))


@mark.lab_has_subcloud
def test_verify_backup_local_simplex_images(request):
    """
    Verify Backup of registry container images

    Testcase steps:
            - Pull, tag and push a test image to local registry
            - Create backup of subcloud and registry backup
            - Made a Subcloud Restore
            - Check if the test image was restored
    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    local_path = f"/opt/platform-backup/backups/{release}/"

    def teardown():
        get_logger().log_info("Removing test files")
        FileKeywords(central_ssh).delete_folder_with_sudo("subcloud_backup.yaml")
        FileKeywords(central_ssh).delete_folder_with_sudo(f"{local_path}{subcloud_name}_platform_backup_*.tgz")

    request.addfinalizer(teardown)

    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, subcloud=subcloud_name, path=f"{local_path}{subcloud_name}_platform_backup_*.tgz", local_only=True, registry=True)
