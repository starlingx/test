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
        Upload backup file(s) from local to controller using backup_software_info.txt

        Args:
            local_backup_folder_path (str): Path on local test machine
            remote_backup_dir (str): Path on controller where backup files are placed

        Returns:
            bool: Whether all uploads were successful
        """
        get_logger().log_info("Using backup_software_info.txt to identify backup files")
        files_to_upload = self.get_backup_files_names_from_list(local_backup_folder_path)

        if not files_to_upload:
            get_logger().log_error("No backup files found in backup_software_info.txt")
            raise Exception("No backup files identified from backup_software_info.txt")

        get_logger().log_info(f"Found {len(files_to_upload)} files to upload: {files_to_upload}")

        upload_results = []
        for file_name in files_to_upload:
            local_path = os.path.join(local_backup_folder_path, file_name)
            remote_path = os.path.join(remote_backup_dir, file_name)

            if not os.path.exists(local_path):
                get_logger().log_error(f"Local backup file not found: {local_path}")
                upload_results.append(False)
                continue

            get_logger().log_info(f"Uploading {file_name}")
            upload_status = FileKeywords(self.ssh_connection).upload_file(local_path, remote_path)
            upload_results.append(upload_status)

        return all(upload_results)

    def get_backup_files_names_from_list(self, local_backup_folder_path: str) -> list:
        """
        Read backup filenames from the 'Backup Files:' section of backup_software_info.txt

        Args:
            local_backup_folder_path (str): Path on local test machine containing the file

        Returns:
            list: List of backup filenames found in the file
        """
        backup_list_path = os.path.join(local_backup_folder_path, "backup_software_info.txt")

        if not os.path.exists(backup_list_path):
            get_logger().log_error(f"Software info file not found: {backup_list_path}")
            return []

        try:
            with open(backup_list_path, 'r') as f:
                lines = f.read().strip().split('\n')

            backup_files = []
            in_backup_section = False
            for line in lines:
                stripped = line.strip()
                if stripped == "Backup Files:":
                    in_backup_section = True
                    continue
                if in_backup_section and stripped:
                    backup_files.append(stripped)

            get_logger().log_info(f"Found {len(backup_files)} backup files from software list: {backup_files}")
            return backup_files

        except Exception as e:
            get_logger().log_error(f"Error reading software list file: {str(e)}")
            return []

    def upload_backup_software_info(self, local_backup_folder_path: str, remote_backup_dir: str) -> bool:
        """
        Upload backup_software_info.txt file from local to controller
        
        Args:
            local_backup_folder_path (str): Path on local test machine
            remote_backup_dir (str): Path on controller where file should be placed
            
        Returns:
            bool: Whether upload was successful
        """
        software_info_file = "backup_software_info.txt"
        local_path = os.path.join(local_backup_folder_path, software_info_file)
        remote_path = os.path.join(remote_backup_dir, software_info_file)
        
        if not os.path.exists(local_path):
            get_logger().log_error(f"Software info file not found: {local_path}")
            return False
            
        get_logger().log_info(f"Uploading {software_info_file}")
        return FileKeywords(self.ssh_connection).upload_file(local_path, remote_path)


