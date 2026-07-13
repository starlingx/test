from pytest import fail, mark

from framework.ssh.ssh_connection import SSHConnection
from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords

central_backup_dir = "/opt/dc-vault/backups/"
local_backup_dir = "/opt/platform-backup/backups/"

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

def restore_backup(central_ssh: SSHConnection, request, subcloud_name, local: bool = False, override_values: str = None, registry: bool = False, prestage_subcloud: bool = False, with_install: bool = True, auto_restore: bool = False, factory: bool = False):
    """Restore a subcloud backup from either central or local storage.

    Args:
        central_ssh (SSHConnection): SSH connection to the active controller.
        request: pytest request object used to register teardown finalizers.
        subcloud_name (str): Name of the subcloud to restore.
        local (bool): If True, restore from local subcloud storage. Defaults to False.
        override_values (str): Path to a restore values yaml file. Defaults to None.
        registry (bool): If True, restore registry images as well. Defaults to False.
        prestage_subcloud (bool): If True, prestage the subcloud before restoring. Defaults to False.
        with_install (bool): If True, attempt restore operation with install. Defaults to True.
        auto_restore (bool): If True, trigger the auto-restore flow. Defaults to False.
        factory (bool): If True, use the factory restore flow. Defaults to False.
    """
    # Gets the subcloud sysadmin password needed for backup creation and deletion on local_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    if prestage_subcloud:
        # Prestage subcloud
        get_logger().log_info(f"Subcloud selected for prestage: {subcloud_name}")
        DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name, subcloud_password)

        # validate prestage status
        sc_prestage_status = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
        # Verify that the prestage is completed successfully
        validate_equals(sc_prestage_status, "complete", f"subcloud {subcloud_name} successfully.")

    if factory:
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
        # Restore subcloud remote backup
        dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, factory=factory)

    elif local:
        if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", True)) < 1:
            fail(f"No backup found for {subcloud_name} locally.")

        def teardown():
            teardown_local(subcloud_name, subcloud_sw_version)

        request.addfinalizer(teardown)

        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
        # Restore subcloud remote backup
        dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, local_only=True, with_install=with_install, release=subcloud_sw_version, restore_values_path=override_values, registry=registry, auto_restore=auto_restore)
    else:
        if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/",
                                                          True)) < 1:
            fail(f"No backup found for {subcloud_name} in central cloud.")

        def teardown():
            teardown_central(subcloud_name, subcloud_sw_version)

        request.addfinalizer(teardown)

        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
        # Restore subcloud remote backup
        dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=with_install, release=subcloud_sw_version, restore_values_path=override_values, registry=registry, auto_restore=auto_restore)

def restore_backup_group(central_ssh: SSHConnection, request, local: bool = False):
    """Restore a backup for a subcloud group from either central or local storage.

    Args:
        central_ssh (SSHConnection): SSH connection to the active controller.
        request: pytest request object used to register teardown finalizers.
        local (bool): If True, restore from local subcloud storage. Defaults to False.
    """
    group_name = "TestGroup"
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    if not group_name in [group.name for group in DcmanagerSubcloudGroupKeywords(central_ssh).
          get_dcmanager_subcloud_group_list().get_dcmanager_subcloud_group_list()]:
        fail(f"{group_name} not found in group list.")

    subcloud_list = []
    for subcloud_obj in (DcmanagerSubcloudGroupKeywords(central_ssh).get_dcmanager_subcloud_group_list_subclouds(group_name).get_dcmanager_subcloud_group_list_subclouds()):
        if subcloud_obj.get_name():
            subcloud_list.append(subcloud_obj.get_name())

    # Gets the subcloud sysadmin password needed for backup retore.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown_group():
        get_logger().log_teardown_step("Removing the created subcloud group during teardown")
        for subcloud in subcloud_list:
            if local:
                teardown_local(subcloud, subcloud_sw_version)
            else:
                teardown_central(subcloud, str(subcloud_sw_version))
            get_logger().log_teardown_step(f"Removing {subcloud} from group.")
            DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud, "group", "Default")

            if DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud).get_management() == "unmanaged":
                get_logger().log_teardown_step(f"Managing subcloud {subcloud}")
                DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud, 10)

        DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_delete(group_name)

    request.addfinalizer(teardown_group)

    for subcloud_name in subcloud_list:
        subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
        if local:
            subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
            get_logger().log_test_case_step(f"Checking if backup was created in {subcloud_name}")
            if len(FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_backup_dir}{subcloud_sw_version}/", is_sudo=True)) < 1:
                fail(f"{subcloud_name} backup not created locally.")
        else:
            get_logger().log_test_case_step("Checking if backup was created on Central")
            if len(FileKeywords(central_ssh).get_files_in_dir(f"{central_backup_dir}{subcloud_name}/{subcloud_sw_version}/", True)) < 1:
                fail(f"No backup found for {subcloud_name} in central cloud.")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)

    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, group=group_name, with_install=True, subcloud_list=subcloud_list, local_only=local)

    for subcloud_name in subcloud_list:
        DcManagerSubcloudListKeywords(central_ssh).validate_subcloud_availability_status(subcloud_name)

def ensure_running_on_controller(central_ssh, controller: str):
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() != controller:
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_central_backup(request):
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
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(
        backup_status="complete-central").get_name()
    restore_backup(central_ssh, request, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup(request):
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

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(
        backup_status="complete-local").get_name()
    restore_backup(central_ssh, request, subcloud_name, local=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_central_backup_n_minus_one(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud. Subcloud must be running an n-1 load.

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

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync").get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")

    restore_backup(central_ssh, request, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_central_backup_n_minus_two(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud. Subcloud must be running an n-2 load.

    Test Steps:
        - Restore an N-2 subcloud from the central stored backup.
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

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync").get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")

    restore_backup(central_ssh, request, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_n_minus_one(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud. Subcloud must be running an n-1 load.

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

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync").get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")

    restore_backup(central_ssh, request, subcloud_name, local=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_n_minus_two(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud. Subcloud must be running an n-2 load.

    Test Steps:
        - Restore an N-2 subcloud from the central stored backup.
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

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync").get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")

    restore_backup(central_ssh, request, subcloud_name, local=True)

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

    # Create restore_values file
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id().get_name()
    restore_backup(central_ssh, request, subcloud_name, override_values="restore_values.yaml")

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

    # Create restore_values file
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id().get_name()
    restore_backup(central_ssh, request, subcloud_name, local=True, override_values="restore_values.yaml")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_from_controller_1_central_backup(request):
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

    # Test should run from controller-1
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(
        backup_status="complete-central").get_name()
    restore_backup(central_ssh, request, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_from_controller_1_remote_backup(request):
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

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(
        backup_status="complete-local").get_name()
    restore_backup(central_ssh, request, subcloud_name, local=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_from_controller_1_central_backup_n_minus_one(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud triggered by controller-1. Subcloud must
    be running an n-1 load.

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

    # Test must run from controller-0
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync",
                                                                                        ).get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")

    restore_backup(central_ssh, request, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_from_controller_1_central_backup_n_minus_two(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud triggered by controller-1. Subcloud must
    be running an n-2 load.

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

    # Test must run from controller-0
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync",
                                                                                        ).get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")

    restore_backup(central_ssh, request, subcloud_name)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_from_controller_1_remote_backup_n_minus_one(request):
    """
    Verify subcloud backup restore from a backup stored in
    subcloud triggered by controller-1. Subcloud must
    be running an n-1 load.

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

    # Test must run from controller-0
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync",
                                                                                        ).get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")

    restore_backup(central_ssh, request, subcloud_name, local=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_from_controller_1_remote_backup_n_minus_two(request):
    """
    Verify subcloud backup restore from a backup stored in
    subcloud triggered by controller-1. Subcloud must
    be running an n-2 load.

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

    # Test must run from controller-0
    if active_controller.get_host_name() == "controller-0":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync",).get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")

    restore_backup(central_ssh, request, subcloud_name, local=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_subcloud_restore_central_backup_with_restore_values_n_minus_one(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud with restore values parameter.
    Subcloud must be running an n-1 load.

    Test Steps:
        - Create a Subcloud backup and check it is stored in
          central cloud.
        - Restore the subcloud from the backup passing the
          --restore-values parameter.

    Teardown:
        - Remove files created while the TC was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Create restore_values file
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync").get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    restore_backup(central_ssh, request, subcloud_name, override_values="restore_values.yaml")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_subcloud_restore_central_backup_with_restore_values_n_minus_two(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud with restore values parameter.
    Subcloud must be running an n-2 load.

    Test Steps:
        - Create a Subcloud backup and check it is stored in
          central cloud.
        - Restore the subcloud from the backup passing the
          --restore-values parameter.

    Teardown:
        - Remove files created while the TC was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Create restore_values file
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync").get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    restore_backup(central_ssh, request, subcloud_name, override_values="restore_values.yaml")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_subcloud_restore_remote_backup_with_restore_values_n_minus_one(request):
    """
    Verify subcloud backup restore from a backup stored in
    subcloud with restore values parameter.
    Subcloud must be running an n-1 load.

    Test Steps:
        - Create a Subcloud backup and check it is stored in
          central cloud.
        - Restore the subcloud from the backup passing the
          --restore-values parameter.

    Teardown:
        - Remove files created while the TC was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Create restore_values file
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync").get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    restore_backup(central_ssh, request, subcloud_name, local=True, override_values="restore_values.yaml")

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_subcloud_restore_remote_backup_with_restore_values_n_minus_two(request):
    """
    Verify subcloud backup restore from a backup stored in
    subcloud with restore values parameter.
    Subcloud must be running an n-2 load.

    Test Steps:
        - Create a Subcloud backup and check it is stored in
          central cloud.
        - Restore the subcloud from the backup passing the
          --restore-values parameter.

    Teardown:
        - Remove files created while the TC was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Create restore_values file
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(sync_status="out-of-sync").get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    restore_backup(central_ssh, request, subcloud_name, local=True, override_values="restore_values.yaml")

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
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()

    # Test should run from controller-0
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id().get_name()
    restore_backup(central_ssh, request, subcloud_name, registry=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_prestaged_subcloud(request):
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
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()

    # Test should run from controller-0
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id().get_name()
    restore_backup(central_ssh, request, subcloud_name, prestage_subcloud=True, local=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_prestaged_subcloud_n_minus_one(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud triggered by controller-0. Subcloud must
    be prestaged and running an n-1 load.

    Test Steps:
        - Prestage the subcloud with inactive load
        - Restore the subcloud central backup
    Teardown:
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()

    # Test should run from controller-0
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id().get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    restore_backup(central_ssh, request, subcloud_name, prestage_subcloud=True, local=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_remote_backup_prestaged_subcloud_n_minus_two(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud triggered by controller-0. Subcloud must
    be prestaged and running an n-2 load.

    Test Steps:
        - Prestage the subcloud with inactive load
        - Restore the subcloud central backup
    Teardown:
        - Remove files created while the Tc was running.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()

    # Test should run from controller-0
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id().get_name()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())

    validate_not_equals(subcloud_sw_version, required_release, "Validate that subcloud is running with required load.")
    restore_backup(central_ssh, request, subcloud_name, prestage_subcloud=True, local=True)

@mark.p2
@mark.lab_has_min_2_subclouds
def test_restore_group_central_backup(request):
    """
    Verify subcloud group backup restore from a backup stored in
    central cloud.

    Test Steps:
        - Restore the subcloud backup
    Teardown:
        - Remove created test group.
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    restore_backup_group(central_ssh, request)

@mark.p2
@mark.lab_has_min_2_subclouds
def test_restore_group_local_backup(request):
    """
    Verify subcloud backup restore

    Test Steps:
        - Restore the subcloud backup
    Teardown:
        - Remove created test group.
        - Remove files created while the Tc was running.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    restore_backup_group(central_ssh, request, local=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_restore_central_backup_no_install(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud without install.
    Subcloud must be running an active load.

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
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(
        backup_status="complete-central").get_name()
    restore_backup(central_ssh, request, subcloud_name, with_install=False)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_auto_restore_central_backup(request):
    """
    Verify subcloud backup auto-restore from a backup stored in
    central cloud. Subcloud must be running an active load.

    Test Steps:
        - Restore the subcloud backup
    Teardown:
        - Remove backup file used for restore

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    ensure_running_on_controller(central_ssh=central_ssh, controller="controller-0")

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(
        backup_status="complete-central").get_name()
    restore_backup(central_ssh, request, subcloud_name, auto_restore=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_auto_restore_remote_backup(request):
    """
    Verify subcloud backup auto-restore from a backup stored in
    the subcloud. Subcloud must be running an active load.

    Test Steps:
        - Restore the subcloud backup
    Teardown:
        - Remove backup file used in restore.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    ensure_running_on_controller(central_ssh=central_ssh, controller="controller-0")

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id(
        backup_status="complete-local").get_name()
    restore_backup(central_ssh, request, subcloud_name, local=True, auto_restore=True)

@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_factory_restore_backup(request):
    """
    Verify subcloud factory backup restore from a backup
    stored in the subcloud.
    Subcloud must be running an active load.

    Test Steps:
        - Restore the subcloud backup
    Teardown:
        - Remove backup file used in restore.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    ensure_running_on_controller(central_ssh=central_ssh, controller="controller-0")

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = DcManagerSubcloudListKeywords(
        central_ssh).get_dcmanager_subcloud_list().get_specific_subcloud_with_lowest_id().get_name()
    restore_backup(central_ssh, request, subcloud_name, factory=True)
