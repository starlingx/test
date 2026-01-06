from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords


def backup_create_failure_local(subcloud_name: str, local: bool = False):
    """Function to run backup operation for local back up.

    Args:
        subcloud_name (str): subcloud name to back up.
        local (bool): If the backup should be stored on subcloud.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Create a subcloud backup and verify the subcloud backup fails.
    get_logger().log_info(f"Attempt creation of {subcloud_name} backup.")
    dc_manager_backup.create_subcloud_backup_expect_fail(subcloud_password, central_ssh, subcloud=subcloud_name, local_only=local)


def teardown_local(subcloud_name: str, created_file_path: str):
    """Teardown function for local backup.

    Args:
        subcloud_name (str): subcloud name
        created_file_path (str): Created file path.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    get_logger().log_info("Removing test files")
    FileKeywords(central_ssh).delete_folder_with_sudo("subcloud_backup.yaml")
    FileKeywords(subcloud_ssh).delete_folder_with_sudo(f"{subcloud_name}_platform_backup_*.tgz")
    FileKeywords(subcloud_ssh).delete_file(created_file_path)

def teardown_central(backup_path: str, created_file_path: str):
    """Teardown function for central backup.

    Args:
        backup_path (str): central backup path
        created_file_path (str): Created file path.
    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    # Path to where the backup file will store.
    get_logger().log_info("Removing test files during teardown")
    FileKeywords(central_ssh).delete_folder_with_sudo(backup_path)
    FileKeywords(central_ssh).delete_file(created_file_path)


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_space_failure(request):
    """Forced failure of a subcloud backup due to lack of space on local storage.

    Test Steps:
        - Attempt subcloud backup with no space left on local storage.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_by_type(LabTypeEnum.SIMPLEX.value)
    subcloud_name = subcloud.get_name()
    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    created_file_path = FileKeywords(subcloud_ssh).create_file_to_fill_disk_space("/home/sysadmin")
    def teardown():
        teardown_local(subcloud.get_name(), created_file_path)
    request.addfinalizer(teardown)
    backup_create_failure_local(subcloud_name, local=True)

@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_space_failure_default_storage(request):
    """Forced failure of a subcloud backup due to lack of space on local storage.

    Test Steps:
        - Attempt subcloud backup with no space left on local storage.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_by_type(LabTypeEnum.SIMPLEX.value)
    subcloud_name = subcloud.get_name()
    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    created_file_path = FileKeywords(central_ssh).create_file_to_fill_disk_space()
    def teardown():
        teardown_central(subcloud.get_name(), created_file_path)
    request.addfinalizer(teardown)
    backup_create_failure_local(subcloud_name)
