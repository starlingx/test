import time

from pytest import mark

from framework.kpi.time_kpi import TimeKPI
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ansible_playbook.ansible_playbook_keywords import AnsiblePlaybookKeywords
from keywords.cloud_platform.ansible_playbook.restore_files_upload_keywords import RestoreFilesUploadKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sw_patch.software_patch_keywords import SwPatchQueryKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager
from keywords.files.file_keywords import FileKeywords


@mark.p0
def test_restore():
    """
    Test system restore using ansible playbook

    Test Steps:
      - Copy backup file to target controller
      - Run restore playbook
      - Unlock host
      - Validate restore completion
    """

    backup_dir = "/home/sysadmin"
    local_backup_folder_path = "/tmp/bnr"
    ssh_connection = LabConnectionKeywords().get_ssh_for_hostname("controller-0")

    get_logger().log_info("Copy backup files from local to target controller")
    restore_file_status = RestoreFilesUploadKeywords(ssh_connection).restore_file(local_backup_folder_path, backup_dir)
    validate_equals(restore_file_status, True, "Backup file copy to controller")
    get_logger().log_info("Backup file copy to controller completed successfully")

    time_kpi_restore = TimeKPI(time.time())
    get_logger().log_info("Run restore ansible playbook")
    ansible_playbook_restore_output = AnsiblePlaybookKeywords(ssh_connection).ansible_playbook_restore(backup_dir)
    validate_equals(ansible_playbook_restore_output, True, "Ansible restore command execution")

    get_logger().log_info("Unlocking controller host")
    ssh_connection = LabConnectionKeywords().get_ssh_for_hostname("controller-0")
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(active_controller.get_host_name())
    validate_equals(unlock_success, True, "Validate controller was unlocked successfully")
    time_kpi_restore.log_elapsed_time(time.time(), "time taken for system restore")

    # Verify software state matches pre-backup state
    get_logger().log_info("Verifying software state post-restore")
    pre_backup_content = FileKeywords(ssh_connection).read_file(f"{backup_dir}/pre_backup_software_list.txt")
    pre_backup_list = [line.strip() for line in pre_backup_content if line.strip()]

    current_version = CloudPlatformVersionManager.get_sw_version()
    if current_version.is_after_or_equal_to(CloudPlatformSoftwareVersion.STARLINGX_10_0):
        sw_list = SoftwareListKeywords(ssh_connection).get_software_list().get_software_lists()
        post_restore_list = [f"{sw.get_release()}:{sw.get_state()}" for sw in sw_list]
    else:
        sw_patch_output = SwPatchQueryKeywords(ssh_connection).get_sw_patch_query()
        post_restore_list = [f"{patch.get_patch_id()}:{patch.get_state()}" for patch in sw_patch_output.get_patches()]

    validate_equals(sorted(post_restore_list), sorted(pre_backup_list), "Software state matches pre-backup state")
