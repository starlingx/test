import re

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_list_contains, validate_greater_than_or_equal
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.linux.date.date_keywords import DateKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords

BACKUP_PATH = "/opt/dc-vault/backups/"


def verify_backup_central(central_ssh: SSHConnection, subcloud_name: str):
    """Function to central Backup of a subcloud

    Verify backup files are stored in centralized archive
    Verify backup date and backup state of single subcloud

    Args:
        central_ssh (SSHConnection): SSH connection to the active controller
        subcloud_name (str): subcloud name to backup
    """
    release = CloudPlatformVersionManagerClass().get_sw_version()
    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    # Path to where the backup file will store.
    central_path = f"{BACKUP_PATH}{subcloud_name}/{release}"
    files_in_backup_dir = FileKeywords(central_ssh).get_files_in_dir(central_path, is_sudo=True)
    if len(files_in_backup_dir) > 0:
        FileKeywords(central_ssh).delete_folder_with_sudo(central_path)

    # Create a subcloud backup and verify the subcloud backup file in central_path
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)

    get_logger().log_info("Checking if backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")
    get_logger().log_info("Checking Subcloud's backup_status, backup_datetime")
    subcloud_show_object = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object()
    backup_status = subcloud_show_object.get_backup_status()
    backup_datetime = subcloud_show_object.get_backup_datetime()

    backup_date = re.findall(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", backup_datetime)
    current_date = DateKeywords(central_ssh).get_current_date()

    # Verifying that backup has been successfully completed and was created today.
    validate_equals(backup_status, "complete-central", "Verifying that the backup is completed successfully.")
    validate_equals(backup_date[0].strip(), current_date, "Verifying that the backup was created today")

def verify_backup_local(central_ssh: SSHConnection, subcloud_ssh: SSHConnection, subcloud_name: str, release:str, custom_path: bool = False):
    """Verify backup files are stored locally to custom directory

    Args:
        central_ssh (SSHConnection): SSH connection to the active controller
        subcloud_ssh (SSHConnection): SSH connection to the subcloud
        subcloud_name (str): subcloud name to backup
        release (str): subcloud release
        custom_path (bool): If True, store the backup in home directory. Defaults to False
    """
    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    if custom_path:
        get_user = lab_config.get_admin_credentials().get_user_name()
        home_path = f"/home/{get_user}/"
        backup_yaml_path = f"{home_path}subcloud_backup.yaml"

        get_logger().log_info("Creating the custom yaml to store backup")
        FileKeywords(central_ssh).create_file_with_echo(backup_yaml_path, f'backup_dir: {home_path}')

        get_logger().log_info("Checking if the yaml was created")
        FileKeywords(central_ssh).file_exists(backup_yaml_path)

        dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{home_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, backup_yaml=backup_yaml_path)
    else:
        backup_path = f"/opt/platform-backup/backups/{release}/"
        files_in_backup_dir = FileKeywords(subcloud_ssh).get_files_in_dir(backup_path, is_sudo=True)

        if len(files_in_backup_dir) > 0:
            FileKeywords(subcloud_ssh).delete_folder_with_sudo(backup_path)

        # Create a subcloud backup and verify the subcloud backup file in local custom path.
        get_logger().log_info(f"Create {subcloud_name} backup locally on {backup_path}")
        dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{backup_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

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
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    verify_backup_central(central_ssh, subcloud_name)

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
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    verify_backup_central(central_ssh, subcloud_name)

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
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_release = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    verify_backup_local(central_ssh, subcloud_ssh, subcloud_name, release=str(subcloud_release))

@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_custom_path_simplex(request):
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
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_release = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    verify_backup_local(central_ssh, subcloud_ssh, subcloud_name, release=str(subcloud_release), custom_path=True)

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
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_release = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    verify_backup_local(central_ssh, subcloud_ssh, subcloud_name, release=str(subcloud_release))

@mark.p0
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
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    subcloud_list = []
    for subcloud_name in ConfigurationManager.get_lab_config().get_subcloud_names():
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)

        # Only adds Simplex and in-sync subclouds.
        if sc_config.get_lab_type() == "Simplex":
            sync_status = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name).get_sync()
            if sync_status == "in-sync":
                subcloud_list.append(subcloud_name)

    validate_greater_than_or_equal(len(subcloud_list), 1, "Validate subcloud list is composed for more than one subcloud")

    for subcloud_name in subcloud_list:
        # Prechecks Before Back-Up:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
        obj_health = HealthKeywords(subcloud_ssh)
        obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    central_path = f"/opt/dc-vault/backups/{subcloud_name}/{release}/"

    # Create subcloud group TestGroup
    DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_add(group_name="TestGroup")
    # Adds subcloud to TestGroup
    DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud_name=subcloud_name, update_attr="group", update_value="TestGroup")

    group_list = DcmanagerSubcloudGroupKeywords(central_ssh).get_dcmanager_subcloud_group_list_subclouds("TestGroup").get_dcmanager_subcloud_group_list_subclouds()
    subclouds = [subcloud.get_name() for subcloud in group_list]
    validate_list_contains(subcloud_name, subclouds, "Verifies if the subcloud name is in the list of subclouds.")

    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}{subcloud_name}_platform_backup_*.tgz", group="TestGroup", subcloud_list=[subcloud_name], release=str(release))

    for subcloud_name in subcloud_list:
        get_logger().log_info("Checking if backup was created on Central")
        DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

@mark.p0
@mark.lab_has_subcloud
def test_verify_backup_remote_simplex_group(request):
    """
    Verify remote backup of subcloud group

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

    get_logger().log_test_case_step("Retrieving ssh key and software release.")
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    subcloud_list = []
    for subcloud_name in ConfigurationManager.get_lab_config().get_subcloud_names():
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)

        # Only adds Simplex and in-sync subclouds.
        if sc_config.get_lab_type() == "Simplex":
            sync_status = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(
                subcloud_name).get_sync()
            if sync_status == "in-sync":
                subcloud_list.append(subcloud_name)

    validate_greater_than_or_equal(len(subcloud_list), 1, "Validate subcloud list is composed for more than one subcloud")

    for subcloud_name in subcloud_list:
        # Prechecks Before Back-Up:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
        obj_health = HealthKeywords(subcloud_ssh)
        obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    get_logger().log_test_case_step("Retrieving subcloud sysadmin password.")
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    central_path = f"/opt/dc-vault/backups/{subcloud_name}/{release}/"

    # Create subcloud group TestGroup
    get_logger().log_test_case_step("Creating subcloud group.")
    DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_add(group_name="TestGroup")

    for subcloud_name in subcloud_list:
        # Adds subcloud to TestGroup
        get_logger().log_test_case_step(f"Adding {subcloud_name} to group.")
        DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud_name=subcloud_name, update_attr="group", update_value="TestGroup")

    group_list = DcmanagerSubcloudGroupKeywords(central_ssh).get_dcmanager_subcloud_group_list_subclouds("TestGroup").get_dcmanager_subcloud_group_list_subclouds()
    subclouds = [subcloud.get_name() for subcloud in group_list]
    validate_equals(subclouds, subcloud_list, "Checking Subcloud's assigned to the group correctly")

    get_logger().log_test_case_step("Creating subclouds backup on subclouds.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}{subcloud_name}_platform_backup_*.tgz", group="TestGroup", subcloud_list=[subcloud_name], release=str(release), local_only=True)

    for subcloud_name in subcloud_list:
        get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
        DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

@mark.p0
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

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    local_path = f"/opt/platform-backup/backups/{release}/"

    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, subcloud=subcloud_name, path=f"{local_path}{subcloud_name}_platform_backup_*.tgz", local_only=True, registry=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_remote_backup_active_load(request):
    """
    Verify subcloud backup is created and stored in subcloud.

    Test Steps:
        - Verify if the active controller is controller-1,
          if not, swact to it.
        - Create a Subcloud backup and check it is stored
          in the subcloud.
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_release = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    def teardown():

        get_logger().log_teardown_step("Swact back to controller-0")
        if active_controller.get_host_name() == "controller-1":
            SystemHostSwactKeywords(central_ssh).host_swact()
            SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    request.addfinalizer(teardown)
    verify_backup_local(central_ssh, subcloud_ssh, subcloud_name, release=str(subcloud_release))

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_central_backup_active_load(request):
    """
    Verify subcloud backup is created and stored centrally.

    Test Steps:
        - Verify if the active controller is controller-1,
          if not, swact to it.
        - Create a Subcloud backup and check it is stored
          centrally on the System Controller.
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[1]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health


    def teardown():

        get_logger().log_teardown_step("Swact back to controller-0")
        if active_controller.get_host_name() == "controller-1":
            SystemHostSwactKeywords(central_ssh).host_swact()
            SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    request.addfinalizer(teardown)

    verify_backup_central(central_ssh, subcloud_name)

@mark.p0
@mark.subcloud_lab_is_standard
def test_verify_backup_central_std(request):
    """Central Backup of a standard subcloud

    Test Steps:
        - Backup subcloud to store the file on the System Controller
        - Verify the subcloud backup file is transferred to the centralized
    default location
        - Check backup match current Date and if it is complete
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    verify_backup_central(central_ssh, subcloud_name)

@mark.p0
@mark.subcloud_lab_is_standard
def test_verify_backup_local_std(request):
    """Local Backup of a standard subcloud

    Test Steps:
        - Create a YAML file and add backup backup_dir parameter
        - Verify file created on the System Controller
        - Run dcmanager CLI Backup with --local-only --backup-values
        - Verify the backup files are stored locally (subcloud) using
    the configured path.
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_release = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    verify_backup_local(central_ssh, subcloud_ssh, subcloud_name, release=str(subcloud_release))

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_central_with_backup_values(request):
    """
    Verify subcloud backup with backup values. Subcloud must be
    running an active load.

    Test Steps:
        - Create a Subcloud backup passing --backup-values
          parameter and check it is stored in central cloud.

    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Create backup_values yaml
    FileKeywords(central_ssh).create_file_with_echo(f"{subcloud_name}_backup_values.yaml", 'exclude_dirs: "/opt/patching/**/*"')

    # Path to where the backup file will store.
    central_path = "/opt/dc-vault/backups/"

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on central cloud.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}/{subcloud_name}/{release}", subcloud=subcloud_name, backup_yaml=f"{subcloud_name}_backup_values.yaml")

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_with_backup_values(request):
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
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_release = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Create backup_values yaml
    FileKeywords(central_ssh).create_file_with_echo(f"{subcloud_name}_backup_values.yaml", 'exclude_dirs: "/opt/patching/**/*"')

    # Path to where the backup file will store.
    local_path = f"/opt/platform-backup/backups/{subcloud_release}/"

    get_logger().log_info(f"Create {subcloud_name} backup locally on {local_path}")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, backup_yaml=f"{subcloud_name}_backup_values.yaml")

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")
