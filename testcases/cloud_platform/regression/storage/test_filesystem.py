from pytest import fail, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.linux.vgdisplay_keywords import VgdisplayKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.controllerfs.objects.system_controllerfs_output import SystemControllerFSOutput
from keywords.cloud_platform.system.controllerfs.system_controllerfs_keywords import SystemControllerFSKeywords
from keywords.cloud_platform.system.host.system_host_fs_keywords import SystemHostFSKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


def check_free_space():
    """
    Check whether there is enough free space to run tests.
    """
    required_space = 10
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    free_space = VgdisplayKeywords(ssh_connection).get_cgts_vg_free_space()

    get_logger().log_info(f"Available free space on the system is: {free_space}")
    if required_space > free_space:
        fail(f"Not enough free space ({required_space} GB) to complete test")


def check_and_increase_backup_fs(ssh_connection: SSHConnection, controllerfs_list: SystemControllerFSOutput) -> None:
    """
    Check backup fs size and increase it if needed.

    Backup size rule: backup >= platform + database + BACKUP_OVERHEAD.
    If the current backup size on any controller is less than the calculated
    required size, it will be increased.

    Args:
        ssh_connection (SSHConnection): Active SSH connection to the system.
        controllerfs_list (SystemControllerFSOutput): The current controllerfs list.

    Returns:
        None: This function does not return any value.
    """
    BACKUP_OVERHEAD = 5
    fs_lookup = {fs.get_name(): fs.get_size() for fs in controllerfs_list.get_filesystems()}

    database_size = fs_lookup.get("database")
    platform_size = fs_lookup.get("platform")

    if database_size is None or platform_size is None:
        get_logger().log_info("Skipping backup check: database or platform fs not found in controllerfs list")
        return

    new_backup_size = (database_size + 1) + (platform_size + 1) + BACKUP_OVERHEAD
    get_logger().log_info(f"Required backup size: {new_backup_size} GiB (database={database_size + 1} + platform={platform_size + 1} + overhead={BACKUP_OVERHEAD})")

    host_fs_keywords = SystemHostFSKeywords(ssh_connection)
    controllers = SystemHostListKeywords(ssh_connection).get_controllers()

    for controller in controllers:
        hostname = controller.get_host_name()
        host_fs_list = host_fs_keywords.get_system_host_fs_list(hostname)
        backup_fs = host_fs_list.get_host_fs("backup")
        if backup_fs is None:
            get_logger().log_info(f"No backup fs found on {hostname}, skipping")
            continue
        current_size = backup_fs.get_size()
        if current_size < new_backup_size:
            get_logger().log_info(f"Increasing backup on {hostname} from {current_size} GiB to {new_backup_size} GiB")
            host_fs_keywords.system_host_fs_modify(hostname, "backup", new_backup_size)
            host_fs_keywords.wait_for_fs_state(hostname, "backup", expected_state="In-Use")
        else:
            get_logger().log_info(f"Backup on {hostname} is already sufficient ({current_size} GiB >= {new_backup_size} GiB)")


@mark.p1
@mark.lab_has_min_space_30G
def test_increase_controllerfs():
    """
    This test increases the size of the various controllerfs filesystems all at
    once.

    Test Steps:
    - Query the filesystem for their current size
    - Increase the size of each filesystem at once

    Assumptions:
    - There is sufficient free space to allow for an increase, otherwise fail
      test.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_controller_fs_keywords = SystemControllerFSKeywords(ssh_connection)
    alarm_list_keyword = AlarmListKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify sufficient free space in cgts-vg volume group")
    check_free_space()

    get_logger().log_test_case_step("Determine the space available for each drbd filesystem")
    controllerfs_list = system_controller_fs_keywords.get_system_controllerfs_list()

    for fs in controllerfs_list.get_filesystems():
        get_logger().log_info(f"Filesystem: {fs.get_name()}, Size: {fs.get_size()} GiB")
        get_logger().log_info(f"Will attempt to increase {fs.get_name()} from {fs.get_size()} GiB to {fs.get_size() + 1} GiB")

    get_logger().log_test_case_step("Increase backup fs if needed")
    check_and_increase_backup_fs(ssh_connection, controllerfs_list)

    get_logger().log_test_case_step("Increase the size of all filesystems")
    system_controller_fs_keywords.increase_all_controllerfs(controllerfs_list)

    get_logger().log_test_case_step("Wait for configuration out-of-date alarm to clear")
    config_out_of_date_alarm = AlarmListObject()
    config_out_of_date_alarm.set_alarm_id("250.001")
    alarm_list_keyword.wait_for_alarms_cleared([config_out_of_date_alarm])

    get_logger().log_test_case_step("Wait for DRBD sync alarm to clear if not simplex")
    controllers = SystemHostListKeywords(ssh_connection).get_controllers()

    if len(controllers) > 1:
        drbd_sync_alarm = AlarmListObject()
        drbd_sync_alarm.set_alarm_id("400.001")
        alarm_list_keyword.wait_for_alarms_cleared([drbd_sync_alarm])
    else:
        get_logger().log_info("Simplex system detected, skipping DRBD sync alarm check")

    get_logger().log_test_case_step("Confirm the underlying filesystem size matches what is expected")
    updated_list = system_controller_fs_keywords.get_system_controllerfs_list()
    updated_sizes = {fs.get_name(): fs.get_size() for fs in updated_list.get_filesystems()}
    for fs in controllerfs_list.get_filesystems():
        expected_size = fs.get_size() + 1
        validate_equals(updated_sizes[fs.get_name()], expected_size, f"Filesystem '{fs.get_name()}' size after increase")
