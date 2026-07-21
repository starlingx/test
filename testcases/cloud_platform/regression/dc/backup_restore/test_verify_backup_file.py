from pytest import mark, fail

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_greater_than_or_equal, validate_not_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords

BACKUP_PATH = "/opt/dc-vault/backups/"

def remove_home_backup_archives(subcloud_ssh: SSHConnection, home_user: str) -> None:
    """Remove leftover platform-backup archives from the subcloud home directory.

    Custom-path local backups are written under /home and are verification artifacts
    only (restore reads from /opt, not /home). Left in place they push /home past the
    backup size precheck and cause later subcloud backups to fail, so remove any such
    archive before creating a new backup.

    Args:
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.
        home_user (str): Home directory owner whose backup archives should be cleared.
    """
    home_dir = f"/home/{home_user}/"
    for file_name in FileKeywords(subcloud_ssh).get_files_in_dir(home_dir, is_sudo=True):
        if "platform_backup" in file_name and file_name.endswith(".tgz"):
            FileKeywords(subcloud_ssh).delete_file(f"{home_dir}{file_name}")

def verify_backup_central(central_ssh: SSHConnection, subcloud_name: str, backup_values: bool = False):
    """Function to central Backup of a subcloud

    Verify backup files are stored in centralized archive
    Verify backup date and backup state of single subcloud

    Args:
        central_ssh (SSHConnection): SSH connection to the active controller
        subcloud_name (str): subcloud name to backup
        backup_values (bool): If backup should use backup values yaml.
    """
    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    remove_home_backup_archives(subcloud_ssh, lab_config.get_admin_credentials().get_user_name())

    # Path to where the backup file will store.
    central_path = f"{BACKUP_PATH}{subcloud_name}/{subcloud_sw_version}"
    files_in_backup_dir = FileKeywords(central_ssh).get_files_in_dir(central_path, is_sudo=True)
    if len(files_in_backup_dir) > 0:
        FileKeywords(central_ssh).delete_folder_with_sudo(central_path)

    backup_yaml = None
    if backup_values:
        # Create backup_values yaml
        FileKeywords(central_ssh).create_file_with_echo(f"{subcloud_name}_backup_values.yaml",'exclude_dirs: "/opt/patching/**/*"')
        backup_yaml = f"{subcloud_name}_backup_values.yaml"

    # Create a subcloud backup and verify the subcloud backup file in central_path
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name, release=subcloud_sw_version, backup_yaml=backup_yaml)

    get_logger().log_info("Checking if backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

def verify_backup_local(central_ssh: SSHConnection, subcloud_name: str, custom_path: bool = False, registry: bool = False, backup_values: bool = False):
    """Verify backup files are stored locally to custom directory

    Args:
        central_ssh (SSHConnection): SSH connection to the active controller
        subcloud_name (str): subcloud name to backup
        custom_path (bool): If True, store the backup in home directory. Defaults to False
        registry (bool): If True, backup the registry images.
        backup_values (bool): If backup should use backup values yaml.
    """
    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    remove_home_backup_archives(subcloud_ssh, lab_config.get_admin_credentials().get_user_name())
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    backup_yaml = None
    if backup_values:
        # Create backup_values yaml
        FileKeywords(central_ssh).create_file_with_echo(f"{subcloud_name}_backup_values.yaml",'exclude_dirs: "/opt/patching/**/*"')
        backup_yaml = f"{subcloud_name}_backup_values.yaml"

    if custom_path:
        get_user = lab_config.get_admin_credentials().get_user_name()
        home_path = f"/home/{get_user}/"

        # Redirect the local backup to the home directory via a backup-values override
        backup_yaml = f"{subcloud_name}_backup_values.yaml"
        FileKeywords(central_ssh).create_file_with_echo(backup_yaml, f"backup_dir: {home_path}")
        dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{home_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, backup_yaml=backup_yaml)
    else:
        backup_path = f"/opt/platform-backup/backups/{subcloud_sw_version}/"
        files_in_backup_dir = FileKeywords(subcloud_ssh).get_files_in_dir(backup_path, is_sudo=True)

        if len(files_in_backup_dir) > 0:
            FileKeywords(subcloud_ssh).delete_folder_with_sudo(backup_path)

        # Create a subcloud backup and verify the subcloud backup file in local custom path.
        get_logger().log_info(f"Create {subcloud_name} backup locally on {backup_path}")
        dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{backup_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, release=subcloud_sw_version, registry=registry, backup_yaml=backup_yaml)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

def backup_subcloud_group(central_ssh: SSHConnection, release: str, subcloud_type: str, local: bool = False):
    # Gets the lowest subcloud sysadmin password needed for backup creation.

    base_subcloud_name = get_healthy_subcloud()
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(base_subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()
    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    latest_release = CloudPlatformVersionManagerClass().get_sw_version()
    if release < str(latest_release):
        sync_status = "out-of-sync"
    else:
        sync_status = "in-sync"

    subcloud_list = DcManagerSubcloudListKeywords(central_ssh).get_specific_subcloud_list(sync_status=sync_status, subcloud_type=subcloud_type, required_release=release)
    validate_greater_than_or_equal(len(subcloud_list), 2,"Validate subcloud list is composed for more than one subcloud")

    # Create subcloud group TestGroup
    DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_add(group_name="TestGroup")

    for subcloud in subcloud_list:
        validate_subcloud_health(subcloud.get_name())
        # Adds subcloud to TestGroup
        DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud_name=subcloud.get_name(), update_attr="group", update_value="TestGroup")

    group_list = DcmanagerSubcloudGroupKeywords(central_ssh).get_dcmanager_subcloud_group_list_subclouds("TestGroup").get_dcmanager_subcloud_group_list_subclouds()
    subclouds = sorted([subcloud.get_name() for subcloud in group_list])
    subcloud_name_list = sorted([sc.get_name() for sc in subcloud_list])
    validate_equals(subclouds, subcloud_name_list, "Checking Subcloud's assigned to the group correctly")

    if local:
        get_logger().log_test_case_step("Creating subclouds backup on subclouds.")
        dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, group="TestGroup", subcloud_list=subclouds, release=str(release), local_only=True)
    else:
        dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, group="TestGroup", subcloud_list=subclouds, release=str(release))

    for subcloud in subcloud_list:
        if local:
            get_logger().log_info("Checking if backup was created on local storage.")
            DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud.get_name(), expected_status="complete-local")
        else:
            get_logger().log_info("Checking if backup was created on Central")
            DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud.get_name(), expected_status="complete-central")

def validate_subcloud_health(subcloud_name: str) -> bool:
    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health
    get_logger().log_info(f"{subcloud_name} is healthy.")
    return True

def get_healthy_subcloud(release: str = None) -> str:
    """Iterates through subclouds from lab config and returns the first healthy one.

    Returns:
        str: The name of a healthy subcloud.

    Raises:
        pytest.skip: If no healthy subcloud is found.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_list = ConfigurationManager.get_lab_config().get_subcloud_names()
    dcmanager_subcloud_list = [sc.get_name() for sc in DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects()]
    for subcloud_name in subcloud_list:
        if subcloud_name not in dcmanager_subcloud_list:
            continue
        subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
        if release:
            if release != subcloud_sw_version:
                continue
        try:
            validate_subcloud_health(subcloud_name)
            return subcloud_name
        except TimeoutError:
            continue
    fail("No healthy subcloud available. Skipping test.")

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
    subcloud_name = get_healthy_subcloud()
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
    subcloud_name = get_healthy_subcloud()
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
    subcloud_name = get_healthy_subcloud()
    verify_backup_local(central_ssh, subcloud_name)

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
    subcloud_name = get_healthy_subcloud()
    verify_backup_local(central_ssh, subcloud_name, custom_path=True)

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
    subcloud_name = get_healthy_subcloud()
    verify_backup_local(central_ssh, subcloud_name)

@mark.p0
@mark.lab_has_subcloud
def test_verify_backup_local_images(request):
    """
    Verify Backup of registry container images

    Testcase steps:
            - Pull, tag and push a test image to local registry
            - Create backup of subcloud and registry backup
            - Made a Subcloud Restore
            - Check if the test image was restored
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = get_healthy_subcloud()
    verify_backup_local(central_ssh, subcloud_name, registry=True)

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_remote_backup(request):
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

    subcloud_name = get_healthy_subcloud()
    verify_backup_local(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_central_backup(request):
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


    subcloud_name = get_healthy_subcloud()
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

    subcloud_name = get_healthy_subcloud()
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

    subcloud_name = get_healthy_subcloud()
    verify_backup_local(central_ssh, subcloud_name)

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

    subcloud_name = get_healthy_subcloud()
    verify_backup_central(central_ssh, subcloud_name, backup_values=True)

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

    subcloud_name = get_healthy_subcloud()
    verify_backup_local(central_ssh, subcloud_name, backup_values=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_on_central_n_minus_one_simplex(request):
    """Verify subcloud with n-1 load backup on central

    Test Steps:
        - Create a Subcloud backup and check it on Central path
        - Check if the backup was created successfully.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_central(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_on_central_n_minus_two_simplex(request):
    """Verify subcloud with n-2 load backup on central

    Test Steps:
        - Create a Subcloud backup and check it on Central path
        - Check if the backup was created successfully.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_central(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_n_minus_one_simplex(request):
    """Verify subcloud with n-1 load backup on local

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Check if the backup was created successfully.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_local(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_local_n_minus_two_simplex(request):
    """Verify subcloud with n-2 load backup on local

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Check if the backup was created successfully.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_local(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_verify_backup_on_central_n_minus_one_duplex(request):
    """Verify subcloud with n-1 load backup on central

    Test Steps:
        - Create a Subcloud backup and check it on Central path
        - Check if the backup was created successfully.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_central(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_verify_backup_on_central_n_minus_two_duplex(request):
    """Verify subcloud with n-2 load backup on central

    Test Steps:
        - Create a Subcloud backup and check it on Central path
        - Check if the backup was created successfully.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_central(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_verify_backup_local_n_minus_one_duplex(request):
    """Verify subcloud with n-1 load backup on local

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Check if the backup was created successfully.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_local(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_verify_backup_local_n_minus_two_duplex(request):
    """Verify subcloud with n-2 load backup on local

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Check if the backup was created successfully.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_local(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_backup_on_central_n_minus_one(request):
    """Verify subcloud with n-1 load backup on central from controller-1.

    Test Steps:
        - Swact to controller-1 if controller-0 is the active controller.
        - Create a Subcloud backup and check it on Central path
        - Check if the backup was created successfully.
    Teardown:
        - Swact back to controller-0

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-0":
        get_logger().log_test_case_step("Swact to controller-1.")
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_central(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_backup_on_central_n_minus_two(request):
    """Verify subcloud with n-2 load backup on central from controller-1.

    Test Steps:
        - Swact to controller-1 if controller-0 is the active controller.
        - Create a Subcloud backup and check it on Central path
        - Check if the backup was created successfully.
    Teardown:
        - Swact back to controller-0

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-0":
        get_logger().log_test_case_step("Swact to controller-1.")
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_central(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_backup_local_n_minus_one(request):
    """Verify subcloud with n-1 load backup in the subcloud from controller-1.

    Test Steps:
        - Swact to controller-1 if controller-0 is the active controller.
        - Create a Subcloud backup and check it is in the subcloud backup path
        - Check if the backup was created successfully.
    Teardown:
        - Swact back to controller-0

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-0":
        get_logger().log_test_case_step("Swact to controller-1.")
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_local(central_ssh, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_backup_local_n_minus_two(request):
    """Verify subcloud with n-2 load backup in the subcloud from controller-1.

    Test Steps:
        - Swact to controller-1 if controller-0 is the active controller.
        - Create a Subcloud backup and check it is in the subcloud backup path
        - Check if the backup was created successfully.
    Teardown:
        - Swact back to controller-0

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-0":
        get_logger().log_test_case_step("Swact to controller-1.")
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    subcloud_name = get_healthy_subcloud(release=required_release)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    verify_backup_local(central_ssh, subcloud_name)

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
    backup_subcloud_group(central_ssh, str(release), subcloud_type="Simplex")

@mark.p0
@mark.lab_has_subcloud
def test_verify_backup_central_simplex_group_n_minus_one(request):
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
    target_release = CloudPlatformVersionManagerClass().get_last_major_release()
    backup_subcloud_group(central_ssh, str(target_release), subcloud_type="Simplex")

@mark.p0
@mark.lab_has_subcloud
def test_verify_backup_central_simplex_group_n_minus_two(request):
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
    target_release = CloudPlatformVersionManagerClass().get_second_last_major_release()
    backup_subcloud_group(central_ssh, str(target_release), subcloud_type="Simplex")

@mark.p0
@mark.lab_has_subcloud
def test_verify_backup_remote_simplex_group(request):
    """
    Verify backup of subcloud group for remote backup and
    N load.

    Test Steps:
        - Create a Subcloud group
        - Assign subcloud to group
        - Verify the subcloud backup file is stored locally.
        - Check backup match current Date and if it is complete
    Teardown:
        - Remove Test Group
        - Remove files created while the Tc was running.
    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()
    backup_subcloud_group(central_ssh, str(release), subcloud_type="Simplex", local=True)

@mark.p0
@mark.lab_has_subcloud
def test_verify_backup_remote_simplex_group_n_minus_one(request):
    """
    Verify backup of subcloud group for remote backup and
    N-1 load.

    Test Steps:
        - Create a Subcloud group
        - Assign subcloud to group
        - Verify the subcloud backup file is stored locally.
        - Check backup match current Date and if it is complete
    Teardown:
        - Remove Test Group
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    target_release = CloudPlatformVersionManagerClass().get_last_major_release()
    backup_subcloud_group(central_ssh, str(target_release), subcloud_type="Simplex", local=True)

@mark.p0
@mark.lab_has_subcloud
def test_verify_backup_remote_simplex_group_n_minus_two(request):
    """
    Verify backup of subcloud group for remote backup and
    N-2 load.

    Test Steps:
        - Create a Subcloud group
        - Assign subcloud to group
        - Verify the subcloud backup file is stored locally.
        - Check backup match current Date and if it is complete
    Teardown:
        - Remove Test Group
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    target_release = CloudPlatformVersionManagerClass().get_second_last_major_release()
    backup_subcloud_group(central_ssh, str(target_release), subcloud_type="Simplex", local=True)
