from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


def backup_creation_rejection(subcloud_name: str):
    """Function to run backup creation command.

    Args:
        subcloud_name (str): subcloud name to back up.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()
    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Create a subcloud backup and verify the subcloud backup file in central_path
    get_logger().log_info(f"Attempt creation of {subcloud_name} backup.")
    dc_manager_backup.create_subcloud_backup_expect_fail(subcloud_password, central_ssh, subcloud=subcloud_name, expect_cmd_rejection=True)


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_command_rejection(request):
    """Forced failure of a subcloud backup command

    Test Steps:
        - Attempt subcloud backup with wrong password for both local
        and central.

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_lower_id_unmanaged_subcloud()
    subcloud_name = subcloud.get_name()
    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    # Prechecks Before Back-Up:
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    backup_creation_rejection(subcloud_name=subcloud_name)
