from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ansible_playbook.ansible_playbook_keywords import AnsiblePlaybookKeywords
from keywords.cloud_platform.ansible_playbook.backup_files_upload_keywords import BackUpFilesUploadKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
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

    backup_file_upload_status = BackUpFilesUploadKeywords(ssh_connection).backup_file(backup_dir, local_backup_folder_path)

    validate_equals(backup_file_upload_status, True, "Backup file upload to local directory")
