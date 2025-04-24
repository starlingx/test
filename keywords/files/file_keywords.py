import time

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class FileKeywords(BaseKeyword):
    """
    Class for file keywords.
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def download_file(self, remote_file_path: str, local_file_path: str) -> bool:
        """
        Method to download a file from the remote host on which the SSH connection is established.

        Args:
            remote_file_path (str): Absolute path of the file to download.
            local_file_path (str): Absolute path (incl file name) to be copied to.

        Returns:
             bool: True if download is successful, False otherwise.

        Raises:
            KeywordException: if unable to copy file.
        """
        try:
            sftp_client = self.ssh_connection.get_sftp_client()
            sftp_client.get(remote_file_path, local_file_path)
        except Exception as e:
            get_logger().log_error(f"Exception while downloading remote file [{remote_file_path}] to [{local_file_path}]. {e}")
            raise KeywordException(f"Exception while downloading remote file [{remote_file_path}] to [{local_file_path}]. {e}")
        return True

    def upload_file(self, local_file_path: str, remote_file_path: str, overwrite: bool = True) -> bool:
        """
        Method to upload a file.

        It will upload from the local host to the remote host on which the SSH connection
        is established.

        Args:
            local_file_path (str): Absolute path for the file to be uploaded.
            remote_file_path (str): Absolute path (incl file name) to upload to.
            overwrite (bool): Whether to overwrite if it already exists.

        Returns:
            bool: True if upload is successful, False otherwise.

        Raises:
            KeywordException: if unable to upload file.
        """
        try:
            if overwrite or not self.file_exists(remote_file_path):
                sftp_client = self.ssh_connection.get_sftp_client()
                sftp_client.put(local_file_path, remote_file_path)
        except Exception as e:
            get_logger().log_error(f"Exception while uploading local file [{local_file_path}] to [{remote_file_path}]. {e}")
            raise KeywordException(f"Exception while uploading local file [{local_file_path}] to [{remote_file_path}]. {e}")
        return True

    def file_exists(self, file_name: str) -> bool:
        """
        Checks if the file exists.

        Args:
            file_name (str): the filename.

        Returns:
            bool: True if exists, False otherwise.
        """
        try:
            sftp_client = self.ssh_connection.get_sftp_client()
            sftp_client.stat(file_name)
            get_logger().log_info(f"{file_name} exists.")
            return True
        except IOError:
            get_logger().log_info(f"{file_name} does not exist.")
            return False

    def delete_file(self, file_name: str) -> bool:
        """
        Deletes the file.

        Args:
            file_name (str): the file name.

        Returns:
            bool: True if delete successful, False otherwise.
        """
        self.ssh_connection.send_as_sudo(f"rm {file_name}")
        return self.file_exists(file_name)

    def get_files_in_dir(self, file_dir: str) -> list[str]:
        """
        Gets a list of filenames in the given dir.

        Args:
            file_dir (str): the directory.

        Returns:
            list[str]: list of filenames.
        """
        sftp_client = self.ssh_connection.get_sftp_client()
        return sftp_client.listdir(file_dir)

    def read_large_file(self, file_name: str, grep_pattern: str = None) -> list[str]:
        """
        Function to read large files and filter.

        We are timing out when reading files over 10000 lines. This function will read the lines in batches.
        The grep pattern will filter lines using grep. If none is specified, all lines are returned.

        Args:
            file_name (str): the full path and filename ex. /var/log/user.log.
            grep_pattern (str): the pattern to use to filter lines ex. 'ptp4l\|phc2sys'.

        Returns:
            list[str]: The output of the file.
        """
        total_output = []
        start_line = 1  # start at line 1
        end_line = 10000  # we can handle 10000 lines without issue
        end_time = time.time() + 300

        grep_arg = ""
        if grep_pattern:
            grep_arg = f"| grep {grep_pattern}"

        while time.time() < end_time:
            output = self.ssh_connection.send(f"sed -n '{start_line},{end_line}p' {file_name} {grep_arg}")
            if not output:  # if we get no more output we are at end of file
                break
            total_output.extend(output)
            start_line = end_line + 1
            end_line = end_line + 10000

        return total_output

    def validate_file_exists_with_sudo(self, path: str) -> bool:
        """
        Validates whether a file or directory exists at the specified path using sudo.

        Args:
            path (str): The path to the file or directory.

        Returns:
            bool: True if the file/directory exists, False otherwise.

        Raises:
            KeywordException: If there is an error executing the SSH command.
        """
        try:
            cmd = f"find {path} -mtime 0"
            output = self.ssh_connection.send_as_sudo(cmd)

            # Handle encoding issues
            output = "".join([line.replace("â€˜", "").replace("â€™", "") for line in output])

            return "No such file or directory" not in output

        except Exception as e:
            get_logger().log_error(f"Failed to check file existence at {path}: {e}")
            raise KeywordException(f"Failed to check file existence at {path}: {e}")

    def create_directory_with_sudo(self, dir_path: str) -> bool:
        """
        Create a directory using sudo if it does not already exist.

        Args:
            dir_path (str): Absolute path to the directory to create.

        Returns:
            bool: True if directory exists or was created successfully.
        """
        if self.validate_file_exists_with_sudo(dir_path):
            get_logger().log_info(f"Directory already exists: {dir_path}")
            return True

        self.ssh_connection.send_as_sudo(f"mkdir -p {dir_path}")
        return self.validate_file_exists_with_sudo(dir_path)

    def create_directory(self, dir_path: str) -> bool:
        """
        Create a directory if it does not already exist.

        Args:
            dir_path (str): Absolute path to the directory to create.

        Returns:
            bool: True if directory exists or was created successfully.
        """
        if self.validate_file_exists_with_sudo(dir_path):
            get_logger().log_info(f"Directory already exists: {dir_path}")
            return True

        self.ssh_connection.send(f"mkdir -p {dir_path}")
        return self.validate_file_exists_with_sudo(dir_path)

    def delete_folder_with_sudo(self, folder_path: str) -> bool:
        """
        Deletes the folder.

        Args:
            folder_path (str): path to the folder.

        Returns:
            bool: True if delete successful, False otherwise.
        """
        self.ssh_connection.send_as_sudo(f"rm -r -f {folder_path}")
        return self.validate_file_exists_with_sudo(folder_path)

    def execute_rsync(self, source_path: str, remote_path: str):
        """Execute rsync command to copy files from source (active controller) to destination

        Args:
            source_path (str): The source path in active controller
            remote_path (str): The destination path
        """
        pasw = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

        # active_controller_ssh.send(f"sshpass -p '{pasw}' rsync -avz {source} {user}@{destination}")
        self.ssh_connection.send(f"sshpass -p '{pasw}' rsync -avz {source_path} {remote_path}")
        self.validate_success_return_code(self.ssh_connection)

    def rename_file(self, old_file_name: str, new_file_name: str):
        """
        Renames the file.

        Args:
            old_file_name (str): path to file to be renamed
            new_file_name (str): path to be set for renamed file
        """
        self.ssh_connection.send_as_sudo(f"mv {old_file_name} {new_file_name}")
