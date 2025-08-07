import os

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


class RestoreFilesUploadKeywords(BaseKeyword):
    """Provides keyword functions to upload backup files to controller before restore."""

    def __init__(self, ssh_connection: str):
        """Initializes AnsiblePlaybookKeywords with an SSH connection.

        Args:
            ssh_connection (str): SSH connection to the target system.
        """
        self.ssh_connection = ssh_connection

    def restore_file(self, local_backup_folder_path: str, remote_backup_dir: str) -> bool:
        """
        Upload backup file(s) from local to controller

        Args:
            local_backup_folder_path (str): Path on local test machine
            remote_backup_dir (str): Path on controller where backup files are placed

        Returns:
            bool: Whether upload was successful
        """
        get_logger().log_info("Checking and uploading backup files to controller")
        backup_files = os.listdir(local_backup_folder_path)
        if not backup_files:
            get_logger().log_error("No backup files found locally")
            raise Exception(f"No backup file available to perform the restore")

        upload_status = False
        for file_name in backup_files:
            if "backup" in file_name:
                local_path = os.path.join(local_backup_folder_path, file_name)
                remote_path = os.path.join(remote_backup_dir, file_name)
                upload_status = FileKeywords(self.ssh_connection).upload_file(local_path, remote_path)                
        return upload_status

