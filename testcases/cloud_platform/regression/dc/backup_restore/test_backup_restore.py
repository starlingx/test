from typing import List

from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.files.file_keywords import FileKeywords

central_backup_dir = "/opt/dc-vault/backups/"
local_backup_dir = "/opt/platform-backup/backups/"

def create_subcloud_group(subcloud_list: List[str]) -> None:
    """
    Creates a subcloud group, assigns subclouds to it, and verifies the assignment.

    Args:
        subcloud_list (List[str]): List of subcloud names to be added to the group.

    Returns:
        None:
    """
    group_name = "Test"
    group_description = "Feature Testing"

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Create a subcloud group
    subcloud_group_keywords = DcmanagerSubcloudGroupKeywords(central_ssh)

    subcloud_group_keywords.dcmanager_subcloud_group_add(group_name)
    subcloud_group_keywords.dcmanager_subcloud_group_update(group_name, "description", group_description)

    # Adding subclouds to group created
    get_logger().log_test_case_step(f"Assigning subclouds to group: {group_name}")
    subcloud_update = DcManagerSubcloudUpdateKeywords(central_ssh)
    for subcloud_name in subcloud_list:
        subcloud_update.dcmanager_subcloud_update(subcloud_name, "group", group_name)

    # Checking Subcloud's assigned to the group correctly
    get_logger().log_test_case_step("Checking Subcloud's in the new group")
    group_list = subcloud_group_keywords.get_dcmanager_subcloud_group_list_subclouds(group_name).get_dcmanager_subcloud_group_list_subclouds()
    subclouds = [subcloud.get_name() for subcloud in group_list]
    validate_equals(subclouds, subcloud_list, "Checking Subcloud's assigned to the group correctly")

def teardown_central(subcloud_name: str, subcloud_sw_version: str):
    """
    Teardown function for central backup restore.

    Args:
        subcloud_name (str): subcloud name.
        subcloud_sw_version (str): subcloud release version.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    if DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name).get_management() == "unmanaged":
        get_logger().log_teardown_step(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

    get_logger().log_teardown_step("Removing used backup from central.")
    FileKeywords(central_ssh).delete_folder_with_sudo(f"{central_backup_dir}/{subcloud_name}/{subcloud_sw_version}")

def teardown_local(subcloud_name: str, subcloud_sw_version: str):
    """
    Teardown function for local backup restore.

    Args:
        subcloud_name (str): subcloud name:
        subcloud_sw_version (str): subcloud release version.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    if DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name).get_management() == "unmanaged":
        get_logger().log_teardown_step(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

    get_logger().log_teardown_step("Removing used backup from local.")
    FileKeywords(subcloud_ssh).delete_folder_with_sudo(f"{local_backup_dir}{subcloud_sw_version}/{subcloud_name}_platform_backup_*.tgz")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_central_backup_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud. Subcloud must be running an active load.

    Test Steps:
        - Restore the subcloud backup
    Teardown:
        - Remove backup file used for restore

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()

    # Test should run from controller-0
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} in central cloud.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on local_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_central(subcloud_name, subcloud_sw_version)
    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud. Subcloud must be running an active load.

    Test Steps:
        - Restore the subcloud backup
    Teardown:
        - Remove backup file used in restore.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on local_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, local_only=True, with_install=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_central_backup_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud. Subcloud must be running an inactive load.

    Test Steps:
        - Restore an N-1 subcloud from the central stored backup.
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()

    # Test must run from controller-0
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    validate_equals(subcloud_sw_version, last_major_release, "Validate subcloud is running N-1 load")

    if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} in central cloud.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_central(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(subcloud_sw_version))

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud. Subcloud must be running an inactive load.

    Test Steps:
        - Restore an N-1 subcloud from local stored backup.
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[2]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    validate_equals(subcloud_sw_version, last_major_release, "Validate subcloud is running N-1 load")

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, local_only=True, release=str(subcloud_sw_version))

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_central_with_backup_values(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud with backup values. Subcloud must be
    running an active load.

    Test Steps:
        - Restore the subcloud from the backup.
        - Verify that backup override was applied.
    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} in central cloud.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Directory to be excluded from the backup
    overrides_value = "/opt/patching/fake_info/fake_info.txt"

    def teardown():
        teardown_central(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(release))

    validate_equals(False, FileKeywords(central_ssh).file_exists(overrides_value), "Validates that the file/dir was not restored.")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_with_backup_values(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud with backup values. Subcloud must be
    running an active load.

    Test Steps:
        - Restore the subcloud from the backup.
        - Verify that backup override was applied.
    Teardown:
        - Remove files created while the Tc was running.

    """

    get_logger().log_test_case_step("Retrieving central ssh key and software release.")
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Back-Up:
    get_logger().log_test_case_step(f"Performing pre-checks on {subcloud_name}.")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    get_logger().log_test_case_step("Retrieving subcloud sysadmin password.")
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Directory to be excluded from the backup
    overrides_value = "/opt/patching/fake_info/fake_info.txt"

    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    get_logger().log_test_case_step(f"Restoring {subcloud_name} backup.")
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(release))

    validate_equals(False, FileKeywords(subcloud_ssh).file_exists(overrides_value), "Validates that the file/dir was not restored.")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_central_with_restore_values(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud with restore values parameter.
    Subcloud must be running an active load.

    Test Steps:
        - Restore the subcloud from the backup passing the
          --restore-values parameter.
    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)
    release = CloudPlatformVersionManagerClass().get_sw_version()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} in central cloud.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Create restore_values file
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    def teardown():
        teardown_central(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(release), restore_values_path="restore_values.yaml")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_with_restore_values(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud. Subcloud must be running an active load.

    Test Steps:
        - Restore the subcloud from the backup passing
          --restore-values parameter.
    Teardown:
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)
    release = CloudPlatformVersionManagerClass().get_sw_version()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Create restore_values file
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, local_only=True, release=str(release), restore_values_path="restore_values.yaml")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_c1_restore_central_backup_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud triggered by controller-1. Subcloud must
    be running an active load.

    Test Steps:
        - Restore the subcloud central backup
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
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} in central cloud.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        get_logger().log_info(f"Managing subcloud {subcloud_name}")
        teardown_central(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_c1_restore_remote_backup_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud triggered by controller-1. Subcloud must
    be running an active load.

    Test Steps:
        - Restore the subcloud local backup
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
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on local_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, local_only=True, with_install=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_c1_restore_central_backup_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud triggered by controller-1. Subcloud must
    be running an inactive load.

    Test Steps:
        - Verify if the active controller is controller-1,
          if not, swact to it.
        - Create a Subcloud backup and check it on local path
        - Restore the subcloud local backup
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    validate_equals(subcloud_sw_version, last_major_release, "Validate subcloud is running N-1 load")

    if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} in central cloud.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_central(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(subcloud_sw_version))

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_c1_restore_remote_backup_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud triggered by controller-1. Subcloud must
    be running an inactive load.

    Test Steps:
        - Restore the subcloud local backup
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    validate_equals(subcloud_sw_version, last_major_release, "Validate subcloud is running N-1 load")

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, local_only=True, release=str(subcloud_sw_version))

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_subcloud_restore_central_backup_with_restore_values_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud with restore values parameter.
    Subcloud must be running an inactive load.

    Test Steps:
        - Create a Subcloud backup and check it is stored in
          central cloud.
        - Restore the subcloud from the backup passing the
          --restore-values parameter.

    Teardown:
        - Remove files created while the TC was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    validate_equals(subcloud_sw_version, last_major_release, "Validate subcloud is running N-1 load")

    if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} in central cloud.")

    # Get subcloud credentials for backup operations
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_central(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    # Create restore_values yaml
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", "wipe_ceph_osds: true")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(subcloud_sw_version), restore_values_path="restore_values.yaml")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_subcloud_restore_local_backup_with_restore_values_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud with restore values parameter.
    Subcloud must be running an inactive load.

    Test Steps:
        - Create a Subcloud backup and check it is stored
          in the subcloud.
        - Restore the subcloud from the backup passing
          --restore-values parameter.

    Teardown:
        - Remove files created while the TC was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    validate_equals(subcloud_sw_version, last_major_release, "Validate subcloud is running N-1 load")

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    # Create backup_values yaml
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", "wipe_ceph_osds: true")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Subcloud Restore Local backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, local_only=True, release=str(subcloud_sw_version), restore_values_path="restore_values.yaml")

@mark.p2
@mark.lab_has_min_2_subclouds
def test_restore_group_central_backup_active_load(request):
    """
    Verify subcloud group backup restore from a backup stored in
    central cloud. Subcloud must be running an active load.

    Test Steps:
        - Create a subcloud group and assign subclouds to it.
        - Create a Subcloud backup and check it is stored in
        central cloud.
        - Restore the subcloud backup
    Teardown:
        - Remove created test group.
        - Remove files created while the Tc was running.

    """
    group_name = "TestGroup"

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    if not group_name in [group.name for group in DcmanagerSubcloudGroupKeywords(central_ssh).
          get_dcmanager_subcloud_group_list().get_dcmanager_subcloud_group_list()]:
        fail(f"{group_name} not found in group list.")

    subcloud_list = []
    for subcloud_name in (DcmanagerSubcloudGroupKeywords(central_ssh).
            get_dcmanager_subcloud_group_list_subclouds(group_name).get_dcmanager_subcloud_group_list_subclouds()):
        if subcloud_name.get_name():
            subcloud_list.append(subcloud_name.get_name())

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

    def teardown_group():
        get_logger().log_teardown_step("Removing the created subcloud group during teardown")
        for subcloud in subcloud_list:
            teardown_central(subcloud, str(release))
            get_logger().log_teardown_step(f"Removing {subcloud} from group.")
            DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud, "group", "Default")

            if DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud).get_management() == "unmanaged":
                get_logger().log_teardown_step(f"Managing subcloud {subcloud}")
                DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud, 10)

        DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_delete(group_name)

    request.addfinalizer(teardown_group)

    for subcloud_name in subcloud_list:
        get_logger().log_test_case_step("Checking if backup was created on Central")
        if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{release}/", True)) < 1:
            fail(f"No backup found for {subcloud_name} in central cloud.")

    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, group=group_name, with_install=True, subcloud_list=subcloud_list)

    for subcloud_name in subcloud_list:
        DcManagerSubcloudListKeywords(central_ssh).validate_subcloud_availability_status(subcloud_name)


@mark.p2
@mark.lab_has_min_2_subclouds
def test_restore_group_local_backup_active_load(request):
    """
    Verify subclothe subcloud.
    Subcloud must be running an active load.

    Test Steps:
        - Create a subcloud group and assign subclouds to it.
        - Create a Subcloud backup and check it is stored in
          the subcloud.
        - Restore the subcloud backup
    Teardown:
        - Remove created test group.
        - Remove files created while the Tc was running.

    """
    group_name = "TestGroup"

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    if not group_name in [group.name for group in DcmanagerSubcloudGroupKeywords(central_ssh).
          get_dcmanager_subcloud_group_list().get_dcmanager_subcloud_group_list()]:
        fail(f"{group_name} not found in group list.")

    subcloud_list = []
    for subcloud_name in (DcmanagerSubcloudGroupKeywords(central_ssh).
            get_dcmanager_subcloud_group_list_subclouds(group_name).get_dcmanager_subcloud_group_list_subclouds()):
        if subcloud_name.get_name():
            subcloud_list.append(subcloud_name.get_name())


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

    def teardown_group():
        get_logger().log_teardown_step("Removing the created subcloud group during teardown")
        for subcloud in subcloud_list:
            get_logger().log_teardown_step("Removing test files from local.")
            teardown_local(subcloud, str(release))
            get_logger().log_teardown_step(f"Removing {subcloud_name} from group.")
            DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud, "group", "Default")

        DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_delete(group_name)

    request.addfinalizer(teardown_group)

    for subcloud_name in subcloud_list:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        get_logger().log_test_case_step(f"Checking if backup was created in {subcloud_name}")
        if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{release}/", is_sudo=True)) < 1:
            fail(f"{subcloud_name} backup not created locally.")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)

    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, group=group_name, with_install=True, subcloud_list=subcloud_list, local_only=True)

    for subcloud_name in subcloud_list:
        DcManagerSubcloudListKeywords(central_ssh).validate_subcloud_availability_status(subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_verify_backup_restore_local_simplex_images(request):
    """
    Verify Backup restore of registry container images

    Testcase steps:
            - Make a Subcloud Restore
            - Check if the test image was restored
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    validate_equals(subcloud_sw_version, last_major_release, "Validate subcloud is running N-1 load")

    backup_dir_files = FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)

    backup_tgz = any(f.startswith(f"{subcloud_name}_platform_backup_") for f in backup_dir_files)
    images_tgz = any(f.startswith(f"{subcloud_name}_image_registry_") for f in backup_dir_files)

    if not backup_tgz or not images_tgz:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Pulls a custom image and adds to subcloud local registry.
    docker_config = ConfigurationManager.get_docker_config()
    docker_img = "hello-world"
    docker_tag = "latest"
    local_registry = docker_config.get_local_registry()
    get_logger().log_test_case_step(f"Add custom docker image to {subcloud_name} registry.")
    DockerImagesKeywords(subcloud_ssh).pull_image(f"{docker_img}:{docker_tag}")
    DockerLoadImageKeywords(subcloud_ssh).tag_docker_image_for_registry(docker_img, docker_tag, local_registry)
    DockerLoadImageKeywords(subcloud_ssh).push_docker_image_to_registry(docker_img, local_registry)

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)
    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, local_only=True, registry=True)

    img_check = DockerImagesKeywords(subcloud_ssh).exists_image(local_registry, docker_img, docker_tag)
    validate_equals(img_check, True, f"Validate that {docker_img} was restored with backup.")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_prestaged_subcloud_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud triggered by controller-0. Subcloud must
    be prestaged and running an active load.

    Test Steps:
        - Prestage the subcloud
        - Restore the subcloud central backup
    Teardown:
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Prestage
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for prestage, backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Prestage subcloud
    get_logger().log_info(f"Subcloud selected for prestage: {subcloud_name}")
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name, subcloud_password)

    # validate prestage status
    sc_prestage_status = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    # Verify that the prestage is completed successfully
    validate_equals(sc_prestage_status, "complete", f"subcloud {subcloud_name} successfully.")

    # validate Healthy status
    obj_health.validate_healty_cluster()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown():
        teardown_central(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_prestaged_subcloud_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud triggered by controller-0. Subcloud must
    be prestaged and running an inactive load.

    Test Steps:
        - Prestage the subcloud with inactive load
        - Restore the subcloud central backup
    Teardown:
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    validate_equals(subcloud_sw_version, last_major_release, "Validate subcloud is running N-1 load")

    if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/")) < 1:
        fail(f"No backup found for {subcloud_name} locally.")

    # Prechecks Before Prestage
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for prestage, backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Prestage subcloud
    get_logger().log_info(f"Subcloud selected for prestage: {subcloud_name}")
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name, subcloud_password)

    # validate prestage status
    sc_prestage_status = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    # Verify that the prestage is completed successfully
    validate_equals(sc_prestage_status, "complete", f"subcloud {subcloud_name} successfully.")

    # validate Healthy status
    obj_health.validate_healty_cluster()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    central_path = "/opt/dc-vault/backups/"

    def teardown():
        teardown_local(subcloud_name, subcloud_sw_version)

    request.addfinalizer(teardown)

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, release=subcloud_sw_version, with_install=True)
