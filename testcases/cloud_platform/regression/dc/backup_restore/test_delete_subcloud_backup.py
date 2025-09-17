from typing import List

from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_group_keywords import DcmanagerSubcloudGroupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object_filter import DcManagerSubcloudListObjectFilter
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_central(request):
    """
    Verify delete centralized subcloud backup

    Test Steps:
        - Create a Subcloud backup and check it on central path
        - Delete the backup created and the backup is deleted
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    central_path = f"/opt/dc-vault/backups/{subcloud_name}/{release}"

    def teardown():
        get_logger().log_info("Removing test files during teardown")
        FileKeywords(central_ssh).delete_folder_with_sudo("/opt/dc-vault/backups/")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo("/opt/platform-backup/backups/")

    request.addfinalizer(teardown)

    # Create a sbcloud backup
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, path=central_path, subcloud=subcloud_name)

    get_logger().log_info("Checking if backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    # Delete the backup created
    get_logger().log_info(f"Delete {subcloud_name} backup on Central Cloud")
    dc_manager_backup.delete_subcloud_backup(central_ssh, release, path=central_path, subcloud=subcloud_name)


@mark.p2
@mark.lab_has_subcloud
def test_delete_backup_local(request):
    """
    Verify delete subcloud backup on local path

    Test Steps:
        - Create a Subcloud backup and check it on local path
        - Delete the backup created and verify the backup is deleted
    Teardown:
        - Remove files created while the Tc was running.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for backup backup creation and deletion on local_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    local_path = f"/opt/platform-backup/backups/{release}/{subcloud_name}_platform_backup_*.tgz"

    def teardown():
        get_logger().log_info("Removing test files during teardown")
        FileKeywords(subcloud_ssh).delete_folder_with_sudo("/opt/platform-backup/backups/")

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on local")
    dc_manager_backup.create_subcloud_backup(
        subcloud_password,
        subcloud_ssh,
        path=local_path,
        subcloud=subcloud_name,
        local_only=True,
    )

    get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    # path where the backup directory should be checked for deletion.
    path = f"/opt/platform-backup/backups/{release}/"

    # Delete the backup created on subcloud
    get_logger().log_info(f"Delete {subcloud_name} backup on Central Cloud")
    dc_manager_backup.delete_subcloud_backup(
        subcloud_ssh,
        release,
        path=path,
        subcloud=subcloud_name,
        local_only=True,
        sysadmin_password=subcloud_password,
    )


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
    get_logger().log_info(f"Creating subcloud group: {group_name}")
    subcloud_group_keywords = DcmanagerSubcloudGroupKeywords(central_ssh)

    subcloud_group_keywords.dcmanager_subcloud_group_add(group_name)
    subcloud_group_keywords.dcmanager_subcloud_group_update(group_name, "description", group_description)

    # Adding subclouds to group created
    get_logger().log_info(f"Assigning subclouds to group: {group_name}")
    subcloud_update = DcManagerSubcloudUpdateKeywords(central_ssh)
    for subcloud_name in subcloud_list:
        subcloud_update.dcmanager_subcloud_update(subcloud_name, "group", group_name)

    # Checking Subcloud's assigned to the group correctly
    get_logger().log_info("Checking Subcloud's in the new group")
    group_list = subcloud_group_keywords.get_dcmanager_subcloud_group_list_subclouds(group_name).get_dcmanager_subcloud_group_list_subclouds()
    subclouds = [subcloud.get_name() for subcloud in group_list]
    validate_equals(subclouds, subcloud_list, "Checking Subcloud's assigned to the group correctly")


@mark.p2
@mark.lab_has_min_2_subclouds
def test_delete_backup_group_on_central(request):
    """
    Verify delete subcloud group backup on central path

    Test Steps:
        - Create a subcloud group and add 2 subclouds
        - Create a Subcloud backup and check it on central path
        - Delete the backup created and verify the backup is deleted
    Teardown:
        - Remove files created while the Tc was running.
        - Delete the subcloud group
    """
    group_name = "Test"

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Retrieves the subclouds. Considers only subclouds that are online, managed, and synced.
    dcmanager_subcloud_list_input = DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter()
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    dcmanager_subcloud_list_objects_filtered = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_input)

    subcloud_list = [subcloud.get_name() for subcloud in dcmanager_subcloud_list_objects_filtered]
    if len(subcloud_list) < 2:
        get_logger().log_info("At least two subclouds managed are required to run the test")
        fail("At least two subclouds managed are required to run the test")

    for subcloud_name in subcloud_list:
        # Prechecks Before Back-Up:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
        obj_health = HealthKeywords(subcloud_ssh)
        obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the subcloud sysadmin password needed for backup creation.
    subcloud_password = ConfigurationManager.get_lab_config().get_subcloud(subcloud_list[0]).get_admin_credentials().get_password()

    # Create a subcloud group and add 2 subclouds
    create_subcloud_group(subcloud_list)

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown_backup():
        get_logger().log_info("Removing test files during teardown")
        FileKeywords(central_ssh).delete_folder_with_sudo("/opt/dc-vault/backups/")

    request.addfinalizer(teardown_backup)

    def teardown_group():
        get_logger().log_info("Removing the created subcloud group during teardown")
        for subcloud_name in subcloud_list:
            DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud_name, "group", "Default")

        DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_delete(group_name)

    request.addfinalizer(teardown_group)

    # Create a subcloud backup
    get_logger().log_info(f"Create backup on Central Cloud for subcloud group: {group_name}")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, group=group_name, release=release, subcloud_list=subcloud_list)

    for subcloud_name in subcloud_list:
        get_logger().log_info("Checking if backup was created on Central")
        DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    # Delete the backup created
    get_logger().log_info(f"Delete backup on Central Cloud for subcloud group: {group_name}")
    dc_manager_backup.delete_subcloud_backup(central_ssh, release=release, group=group_name, subcloud_list=subcloud_list)


@mark.p2
@mark.lab_has_min_2_subclouds
def test_delete_backup_group_on_local(request):
    """
    Verify delete subcloud group backup on local path

    Test Steps:
        - Create a subcloud group and add 2 subclouds
        - Create a Subcloud backup and check it on local path
        - Delete the backup created and verify the backup is deleted

    Teardown:
        - Remove files created while the Tc was running.
        - Delete the subcloud group

    """
    group_name = "Test"
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Retrieves the subclouds. Considers only subclouds that are online, managed, and synced.
    dcmanager_subcloud_list_input = DcManagerSubcloudListObjectFilter.get_healthy_subcloud_filter()
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    dcmanager_subcloud_list_objects_filtered = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects_filtered(dcmanager_subcloud_list_input)

    subcloud_list = [subcloud.name for subcloud in dcmanager_subcloud_list_objects_filtered]
    if len(subcloud_list) < 2:
        get_logger().log_info("At least two subclouds managed are required to run the test")
        fail("At least two subclouds managed are required to run the test")

    for subcloud_name in subcloud_list:
        # Prechecks Before Back-Up:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
        obj_health = HealthKeywords(subcloud_ssh)
        obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the subcloud sysadmin password needed for backup creation.
    subcloud_password = ConfigurationManager.get_lab_config().get_subcloud(subcloud_list[0]).get_admin_credentials().get_password()

    # Create a subcloud group and add 2 subclouds
    create_subcloud_group(subcloud_list)

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    def teardown_backup():
        get_logger().log_info("Removing test files during teardown")
        for subcloud_name in subcloud_list:
            subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
            FileKeywords(subcloud_ssh).delete_folder_with_sudo("/opt/platform-backup/backups/")

    request.addfinalizer(teardown_backup)

    def teardown_group():
        get_logger().log_info("Removing the created subcloud group during teardown")
        for subcloud_name in subcloud_list:
            DcManagerSubcloudUpdateKeywords(central_ssh).dcmanager_subcloud_update(subcloud_name, "group", "Default")
        DcmanagerSubcloudGroupKeywords(central_ssh).dcmanager_subcloud_group_delete(group_name)

    request.addfinalizer(teardown_group)

    # Create a subcloud backup and check it on local path
    get_logger().log_info(f"Create and check if backup was was created on Central Cloud for subcloud group: {group_name}")
    dc_manager_backup.create_subcloud_backup(subcloud_password, central_ssh, local_only=True, group=group_name, release=release, subcloud_list=subcloud_list)

    for subcloud_name in subcloud_list:
        get_logger().log_info(f"Checking if backup was created on {subcloud_name}")
        DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    # Delete the backup created and verify the backup is deleted
    get_logger().log_info(f"Delete and check if backup was removed on SubClouds for subcloud group: {group_name}")
    dc_manager_backup.delete_subcloud_backup(central_ssh, release=release, local_only=True, group=group_name, sysadmin_password=subcloud_password, subcloud_list=subcloud_list)
