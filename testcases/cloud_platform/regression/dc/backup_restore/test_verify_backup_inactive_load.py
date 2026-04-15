from pytest import mark, fail

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass

central_path = "/opt/dc-vault/backups/"
local_path = "/opt/platform-backup/backups/"

@mark.p2
@mark.lab_has_subcloud
def test_verify_backup_on_central_inactive_load(request):
    """Verify subcloud with inactive load backup on central

    Test Steps:
        - Create a Subcloud backup and check it on Central path
        - Check if the backup was created successfully.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        get_logger().log_test_case_step("Swact to controller-0.")
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(
        subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if subcloud_sw_version != last_major_release:
        fail(f"{subcloud_name} in running {subcloud_sw_version} version, should be {last_major_release}.")

    validate_subcloud_health(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    if FileKeywords(central_ssh).validate_file_exists_with_sudo(f"{central_path}{subcloud_name}/{subcloud_sw_version}"):
        get_logger().log_info("Removing test files.")
        FileKeywords(central_ssh).delete_folder_with_sudo(central_path)

    # Create a sbcloud backup
    # First creation backup
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)

    get_logger().log_info("Checking if inactive load backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    FileKeywords(central_ssh).validate_file_exists_with_sudo(f"{central_path}{subcloud_name}/{subcloud_sw_version}")

@mark.p2
@mark.lab_has_subcloud
def test_verify_backup_local_inactive_load(request):
    """Verify subcloud with inactive load backup on local

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Check if the backup was created successfully.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(central_ssh).get_active_controller()
    standby_controller = SystemHostListKeywords(central_ssh).get_standby_controller()
    if active_controller.get_host_name() == "controller-1":
        get_logger().log_test_case_step("Swact to controller-0.")
        SystemHostSwactKeywords(central_ssh).host_swact()
        SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if subcloud_sw_version != last_major_release:
        fail(f"{subcloud_name} in running {subcloud_sw_version} version, should be {last_major_release}.")

    validate_subcloud_health(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    if FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(f"{local_path}{subcloud_sw_version}"):
        get_logger().log_info("Removing test files.")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(f"{local_path}{subcloud_sw_version}")

    # First creation backup
    # Create a sbcloud backup
    get_logger().log_info(f"Create first backup on {subcloud_name}")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}/{subcloud_sw_version}/", subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    FileKeywords(central_ssh).validate_file_exists_with_sudo(f"{local_path}/{subcloud_sw_version}")

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_backup_on_central_inactive_load(request):
    """Verify subcloud with inactive load backup on central from controller-1.

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

    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    if subcloud_sw_version != last_major_release:
        fail(f"{subcloud_name} in running {subcloud_sw_version} version, should be {last_major_release}.")

    validate_subcloud_health(subcloud_name)

    def teardown():
        if active_controller.get_host_name() == "controller-1":
            get_logger().log_test_case_step("Swact back to controller-0.")
            SystemHostSwactKeywords(central_ssh).host_swact()
            SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    request.addfinalizer(teardown)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    if FileKeywords(central_ssh).validate_file_exists_with_sudo(f"{central_path}{subcloud_name}/{subcloud_sw_version}"):
        get_logger().log_info("Removing test files.")
        FileKeywords(central_ssh).delete_folder_with_sudo(central_path)

    # Create a sbcloud backup
    # First creation backup
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)

    get_logger().log_info("Checking if inactive load backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    FileKeywords(central_ssh).validate_file_exists_with_sudo(f"{central_path}{subcloud_name}/{subcloud_sw_version}")

@mark.p2
@mark.lab_has_subcloud
def test_c1_verify_backup_local_inactive_load(request):
    """Verify subcloud with inactive load backup in the subcloud from controller-1.

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

    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    if subcloud_sw_version != last_major_release:
        fail(f"{subcloud_name} in running {subcloud_sw_version} version, should be {last_major_release}.")

    validate_subcloud_health(subcloud_name)

    def teardown():
        if active_controller.get_host_name() == "controller-1":
            get_logger().log_test_case_step("Swact back to controller-0.")
            SystemHostSwactKeywords(central_ssh).host_swact()
            SystemHostSwactKeywords(central_ssh).wait_for_swact(active_controller, standby_controller)

    request.addfinalizer(teardown)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    if FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(f"{local_path}{subcloud_sw_version}"):
        get_logger().log_info("Removing test files.")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo(f"{local_path}{subcloud_sw_version}")

    # First creation backup
    # Create a sbcloud backup
    get_logger().log_info(f"Create first backup on {subcloud_name}")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}{subcloud_sw_version}", subcloud=subcloud_name, local_only=True)

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    FileKeywords(subcloud_ssh).validate_file_exists_with_sudo(f"{local_path}{subcloud_sw_version}")

def validate_subcloud_health(subcloud_name: str):
    """Verifies the health of the subcloud

    Args:
        subcloud_name (str): subcloud to check
    """
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health
