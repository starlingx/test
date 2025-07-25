from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ansible_playbook.ansible_playbook_keywords import AnsiblePlaybookKeywords
from keywords.cloud_platform.ansible_playbook.backup_files_upload_keywords import BackUpFilesUploadKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sw_patch.software_patch_keywords import SwPatchQueryKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager
from keywords.files.file_keywords import FileKeywords


@mark.p0
def test_backup():
    """
    Test system backup using ansible playbook

    Test Steps:
      - Take a system backup
      - Verify backup is successful
      - copy to local test server

    """

    backup_dir = "/opt/backups"
    local_backup_folder_path = "/tmp/bnr"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Capture the state of software releases (or patches for older versions) before backup
    current_version = CloudPlatformVersionManager.get_sw_version()
    if current_version.is_after_or_equal_to(CloudPlatformSoftwareVersion.STARLINGX_10_0):
        get_logger().log_info("Getting software list (24.09+)")
        sw_list = SoftwareListKeywords(ssh_connection).get_software_list().get_software_lists()
        info_list = [f"{sw.get_release()}:{sw.get_state()}" for sw in sw_list]
    else:
        get_logger().log_info("Getting sw-patch query (pre-24.09)")
        sw_patch_output = SwPatchQueryKeywords(ssh_connection).get_sw_patch_query()
        info_list = [f"{patch.get_patch_id()}:{patch.get_state()}" for patch in sw_patch_output.get_patches()]

    FileKeywords(ssh_connection).create_file_with_echo("/tmp/pre_backup_software_list.txt", "\n".join(info_list))

    # Prechecks Before Back-Up:
    get_logger().log_info("Performing pre-checks before back up")
    obj_health = HealthKeywords(ssh_connection)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    get_logger().log_info("Delete old backup files if present in back up directory")
    backup_files = FileKeywords(ssh_connection).get_files_in_dir(backup_dir)
    for backup_file in backup_files:
        if "backup" in backup_file:
            get_logger().log_info(f"Deleting old backup file {backup_file}")
            file_exists_post_deletion = FileKeywords(ssh_connection).delete_file(f"{backup_dir}/{backup_file}")
            validate_equals(file_exists_post_deletion, False, "Old Back up file deletion")

    get_logger().log_info("Run backup ansible playbook")
    ansible_playbook_backup_output = AnsiblePlaybookKeywords(ssh_connection).ansible_playbook_backup(backup_dir)
    validate_equals(ansible_playbook_backup_output, True, "Ansible backup command execution")

    # Copy software list to backup directory
    ssh_connection.send_as_sudo(f"cp /tmp/pre_backup_software_list.txt {backup_dir}/")

    backup_file_upload_status = BackUpFilesUploadKeywords(ssh_connection).backup_file(backup_dir, local_backup_folder_path)

    validate_equals(backup_file_upload_status, True, "Backup file upload to local directory")
