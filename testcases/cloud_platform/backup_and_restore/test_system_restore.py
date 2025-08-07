from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ansible_playbook.ansible_playbook_keywords import AnsiblePlaybookKeywords
from keywords.cloud_platform.ansible_playbook.restore_files_upload_keywords import RestoreFilesUploadKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords

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
    
    get_logger().log_info("Run restore ansible playbook")
    ansible_playbook_restore_output = AnsiblePlaybookKeywords(ssh_connection).ansible_playbook_restore(backup_dir)
    validate_equals(ansible_playbook_restore_output, True, "Ansible restore command execution")

    get_logger().log_info("Unlocking controller host")    
    ssh_connection = LabConnectionKeywords().get_ssh_for_hostname("controller-0")
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(active_controller.get_host_name())
    validate_equals(unlock_success, True, "Validate controller was unlocked successfully")


