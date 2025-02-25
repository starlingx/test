from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import (
    DcManagerSubcloudBackupKeywords,
)
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import (
    DcManagerSubcloudListKeywords,
)
from keywords.cloud_platform.rest.bare_metal.hosts.get_hosts_keywords import (
    GetHostsKeywords,
)
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import (
    SystemHostListKeywords,
)


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
    host = SystemHostListKeywords(central_ssh).get_active_controller().get_host_name()
    host_show_output = GetHostsKeywords().get_hosts().get_system_host_show_object(host)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = (
        dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    )
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Get the sw_version if available (used in vbox environments).
    release = host_show_output.get_sw_version()
    # If sw_version is not available, fall back to software_load (used in physical labs).
    if not release:
        release = host_show_output.get_software_load()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    central_path = f"/opt/dc-vault/backups/{subcloud_name}/{release}"

    def teardown():
        get_logger().log_info("Removing test files during teardown")
        central_ssh.send_as_sudo("rm -r -f /opt/dc-vault/backups/")
        subcloud_ssh.send_as_sudo("rm -r -f /opt/platform-backup/backups/")

    request.addfinalizer(teardown)

    # Create a sbcloud backup
    get_logger().log_info(f"Create {subcloud_name} backup on Central Cloud")
    dc_manager_backup.create_subcloud_backup(
        subcloud_password, central_ssh, central_path, subcloud=subcloud_name
    )

    # Delete the backup created
    get_logger().log_info(f"Delete {subcloud_name} backup on Central Cloud")
    dc_manager_backup.delete_subcloud_backup(
        central_ssh, central_path, release, subcloud=subcloud_name
    )


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
    host = SystemHostListKeywords(central_ssh).get_active_controller().get_host_name()
    host_show_output = GetHostsKeywords().get_hosts().get_system_host_show_object(host)

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = (
        dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    )
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Gets the lowest subcloud sysadmin password needed for backup backup creation and deletion on local_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Get the sw_version if available (used in vbox environments).
    release = host_show_output.get_sw_version()
    # If sw_version is not available, fall back to software_load (used in physical labs).
    if not release:
        release = host_show_output.get_software_load()

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path to where the backup file will store.
    local_path = (
        f"/opt/platform-backup/backups/{release}/{subcloud_name}_platform_backup_*.tgz"
    )

    def teardown():
        get_logger().log_info("Removing test files during teardown")
        subcloud_ssh.send_as_sudo("rm -r -f /opt/platform-backup/backups/")

    request.addfinalizer(teardown)

    # Create a subcloud backup on local
    get_logger().log_info(f"Create {subcloud_name} backup on local")
    dc_manager_backup.create_subcloud_backup(
        subcloud_password,
        subcloud_ssh,
        local_path,
        subcloud=subcloud_name,
        local_only=True,
    )

    # path where the backup directory should be checked for deletion.
    path = f"/opt/platform-backup/backups/{release}/"

    # Delete the backup created on subcloud
    get_logger().log_info(f"Delete {subcloud_name} backup on Central Cloud")
    dc_manager_backup.delete_subcloud_backup(
        subcloud_ssh,
        path,
        release,
        subcloud=subcloud_name,
        local_only=True,
        sysadmin_password=subcloud_password,
    )
