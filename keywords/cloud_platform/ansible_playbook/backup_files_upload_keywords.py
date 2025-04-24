import os

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


class BackUpFilesUploadKeywords(BaseKeyword):
    """Provides keyword functions for ansible playbook commands."""

    def __init__(self, ssh_connection: str):
        """Initializes AnsiblePlaybookKeywords with an SSH connection.

        Args:
            ssh_connection (str): SSH connection to the target system.
        """
        self.ssh_connection = ssh_connection

    def backup_file(self, backup_file_path: str, local_backup_folder_path: str) -> bool:
        """
        Check backup files present in backup playbook path scp backup files to local machine.

        Args:
            backup_file_path (str): backup file path
            local_backup_folder_path (str): Local backup folder path
        Returns:
            bool: Parsed output to verify successful backup
        """
        get_logger().log_info("create a temporary directory in local server to copy the backup files")
        os.makedirs(local_backup_folder_path, exist_ok=True)

        get_logger().log_info("Check backup files present in backup playbook path")
        cmd = f"ls -tr {backup_file_path} | grep --color=never backup"
        backup_files = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)

        file_download_status = False
        for backup_file in backup_files:
            if "backup" in backup_file:
                backup_src_path = (os.path.join(backup_file_path, backup_file)).strip()
                backup_dest_path = os.path.join(local_backup_folder_path, backup_file).strip()

                get_logger().log_info(f"Upload backup file from {backup_src_path} to local {backup_dest_path} path")

                file_download_status = FileKeywords(self.ssh_connection).download_file(backup_src_path, backup_dest_path)

        return file_download_status
