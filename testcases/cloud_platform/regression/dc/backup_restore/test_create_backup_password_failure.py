from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from pytest import mark

from config.lab.objects.lab_type_enum import LabTypeEnum


def backup_create_failure(central_ssh: SSHConnection, subcloud_name: str, central: bool = True):
    """Function to run backup operation for both central
    and local backups.

    Args:
        central_ssh (SSHConnection): SSH connection to the active system controller.
        subcloud_name (str): subcloud name to backup.
        central (bool): if the backup should be stored on central cloud, if False, backup is set to be stored on subcloud. Default value as True.
    """
    subcloud_password = "Fakepassword1234!"

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    if central:
        env = "central"
        local_only = False
    else:
        env = "local"
        local_only = True

    # Create a subcloud backup and verify the subcloud backup file in central_path
    get_logger().log_info(f"Attempt creation of {subcloud_name} backup on {env}")
    dc_manager_backup.create_subcloud_backup_expect_fail(subcloud_password, central_ssh, subcloud=subcloud_name, local_only=local_only)


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_password_failure(request):
    """Forced failure of a subcloud backup

    Test Steps:
        - Attempt subcloud backup with wrong password for both local
        and central.

    """
    system_controller_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )
    subcloud_name = result.get_name()
    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    backup_create_failure(system_controller_ssh, subcloud_name)
    backup_create_failure(system_controller_ssh, subcloud_name, central=False)
