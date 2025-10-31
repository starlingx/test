from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords


@mark.p2
@mark.lab_has_subcloud
def test_restore_central_backup_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud. Subcloud must be running an active load.

    Test Steps:
        - Create a Subcloud backup and check it is stored in
        central cloud.
        - Restore the subcloud backup
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
    central_path = "/opt/dc-vault/backups/"

    def teardown():
        get_logger().log_info(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(central_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on local")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}/{subcloud_name}/{release}", subcloud=subcloud_name)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True)


@mark.p2
@mark.lab_has_subcloud
def test_restore_remote_backup_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud. Subcloud must be running an active load.

    Test Steps:
        - Create a Subcloud backup and check it is stored in
          the subcloud.
        - Restore the subcloud backup
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
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

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
    Verify subcloud backup restore from a backup stored in
    central cloud. Subcloud must be running an inactive load.

    Test Steps:
        - Deploy a subcloud with n-1 release.
        - Create a Subcloud backup and check it on central path
        - Restore the subcloud from the central stored backup
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)
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
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(central_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on central cloud.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}/{subcloud_name}/{subcloud_release}", subcloud=subcloud_name)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(subcloud_release))


@mark.p2
@mark.lab_has_subcloud
def test_restore_remote_backup_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud. Subcloud must be running an inactive load.

    Test Steps:
        - Deploy a subcloud with n-1 load.
        - Create a Subcloud backup and check it is stored
          in the subcloud.
        - Restore the subcloud backup
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)
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
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

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


@mark.p2
@mark.lab_has_subcloud
def test_restore_central_with_backup_values(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud with backup values. Subcloud must be
    running an active load.

    Test Steps:
        - Create a Subcloud backup passing --backup-values
          parameter and check it is stored in central cloud.
        - Restore the subcloud from the backup.
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

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_managed_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
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

    # Create backup_values yaml
    FileKeywords(central_ssh).create_file_with_echo("backup_values.yaml", 'exclude_dirs: "/opt/patching/**/*"')

    # Path to where the backup file will store.
    central_path = "/opt/dc-vault/backups/"

    def teardown():
        get_logger().log_info(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(central_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on central cloud.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}/{subcloud_name}/{release}", subcloud=subcloud_name, backup_yaml="backup_values.yaml")

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(release))


@mark.p2
@mark.lab_has_subcloud
def test_restore_central_with_restore_values(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud with restore values parameter.
    Subcloud must be running an active load.

    Test Steps:
        - Create a Subcloud backup and check it is stored in
          central cloud.
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

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_managed_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
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

    # Create backup_values yaml
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    # Path to where the backup file will store.
    central_path = "/opt/dc-vault/backups/"

    def teardown():
        get_logger().log_info(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(central_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on central cloud.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}/{subcloud_name}/{release}", subcloud=subcloud_name)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(release), restore_values_path="restore_values.yaml")


@mark.p2
@mark.lab_has_subcloud
def test_restore_remote_with_restore_values(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud. Subcloud must be running an active load.

    Test Steps:
        - Create a Subcloud backup and check it is stored
          in the subcloud.
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

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_managed_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
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

    # Create backup_values yaml
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", 'wipe_ceph_osds: "false"')

    # Path to where the backup file will be stored.
    local_path = f"/opt/platform-backup/backups/{release}"

    def teardown():
        get_logger().log_info(f"Managing subcloud {subcloud_name}")
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(local_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on remote")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=local_path, subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, local_only=True, release=str(release), restore_values_path="restore_values.yaml")


@mark.p2
@mark.lab_has_subcloud
def test_c1_restore_central_backup_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    central cloud triggered by controller-1. Subcloud must
    be running an active load.

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
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

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
def test_c1_restore_remote_backup_active_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud triggered by controller-1. Subcloud must
    be running an active load.

    Test Steps:
        - Verify if the active controller is controller-1,
          if not, swact to it.
        - Create a Subcloud backup and check it is stored
          in the subcloud.
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
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

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
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(central_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on central cloud.")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=f"{central_path}/{subcloud_name}/{subcloud_release}", subcloud=subcloud_name)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(subcloud_release))


@mark.p2
@mark.lab_has_subcloud
def test_c1_restore_remote_backup_inactive_load(request):
    """
    Verify subcloud backup restore from a backup stored in
    the subcloud triggered by controller-1. Subcloud must
    be running an inactive load.

    Test Steps:
        - Verify if the active controller is controller-1,
          if not, swact to it.
        - Create a Subcloud backup and check it is stored
          in the subcloud.
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
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

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


@mark.p2
@mark.lab_has_subcloud
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
    subcloud_release = CloudPlatformVersionManagerClass().get_last_major_release()

    # Gets the subcloud with the specified release.
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_managed_subcloud = dcmanager_subcloud_list_keywords.get_one_subcloud_by_release(str(subcloud_release))
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

    # Unmanage subcloud
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(central_ssh)
    dcm_sc_manager_kw.get_dcmanager_subcloud_unmanage(subcloud_name, 30)

    # To-Do: Add restore values yaml creation
    # Create restore_values yaml
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", "wipe_ceph_osds: true")

    # Restore subcloud remote backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, release=str(subcloud_release), restore_values_path="restore_values.yaml")

    # Manage the subcloud and validate sync status
    dcm_sc_manager_kw.get_dcmanager_subcloud_manage(subcloud_name, 30)
    DcManagerSubcloudListKeywords(central_ssh).validate_subcloud_sync_status(subcloud_name, expected_sync_status="in-sync")


@mark.p2
@mark.lab_has_subcloud
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
        DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)

        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(local_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on local")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=local_path, subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    # Unmanage subcloud
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(central_ssh)
    dcm_sc_manager_kw.get_dcmanager_subcloud_unmanage(subcloud_name, 30)

    # Create backup_values yaml
    FileKeywords(central_ssh).create_file_with_echo("restore_values.yaml", "wipe_ceph_osds: true")

    # Subcloud Restore Local backup
    dc_manager_backup.restore_subcloud_backup(subcloud_password, central_ssh, subcloud=subcloud_name, with_install=True, local_only=True, release=str(subcloud_release), restore_values_path="restore_values.yaml")

    # Manage the subcloud and validate sync status
    dcm_sc_manager_kw.get_dcmanager_subcloud_manage(subcloud_name, 30)
    DcManagerSubcloudListKeywords(central_ssh).validate_subcloud_sync_status(subcloud_name, expected_sync_status="in-sync")
