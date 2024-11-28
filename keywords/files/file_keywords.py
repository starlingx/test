from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class FileKeywords(BaseKeyword):
    """
    Class for file keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def download_file(self, remote_file_path: str, local_file_path: str) -> bool:
        """
        Method to download a file from the remote host on which the SSH connection is established
        Args:
            remote_file_path: Absolute path of the file to download.
            local_file_path: Absolute path (incl file name) to be copied to.
        Returns: True if download is successful, False otherwise.
        """
        try:
            sftp_client = self.ssh_connection.get_sftp_client()
            sftp_client.get(remote_file_path, local_file_path)
        except Exception as e:
            get_logger().log_error(f'Exception while downloading remote file [{remote_file_path}] to [{local_file_path}]. {e}')
            raise KeywordException(f'Exception while downloading remote file [{remote_file_path}] to [{local_file_path}]. {e}')
        return True

    def upload_file(self, local_file_path: str, remote_file_path: str, overwrite: bool = True) -> bool:
        """
        Method to upload a file from the local host to the remote host on
        which the SSH connection is established
        Args:
            local_file_path: Absolute path for the file to be uploaded.
            remote_file_path: Absolute path (incl file name) to upload to.
            overwrite: Whether to overwrite if it already exists

        Returns: True if upload is successful, False otherwise.
        """
        try:
            if overwrite or not self.file_exists(remote_file_path):
                sftp_client = self.ssh_connection.get_sftp_client()
                sftp_client.put(local_file_path, remote_file_path)
        except Exception as e:
            get_logger().log_error(f'Exception while uploading local file [{local_file_path}] to [{remote_file_path}]. {e}')
            raise KeywordException(f'Exception while uploading local file [{local_file_path}] to [{remote_file_path}]. {e}')
        return True

    def file_exists(self, file_name) -> bool:
        """
        Checks if the file exists
        Args:
            file_name (): the filename
        Returns: True if exists, False otherwise

        """
        try:
            sftp_client = self.ssh_connection.get_sftp_client()
            sftp_client.stat(file_name)
            get_logger().log_info(f"{file_name} exists.")
            return True
        except IOError:
            get_logger().log_info(f"{file_name} does not exist.")
            return False

    def delete_file(self, file_name):
        """
        Deletes the file
        Args:
            file_name (): the file name

        Returns: True if delete successful, False otherwise

        """
        self.ssh_connection.send_as_sudo(f'rm {file_name}')
        return self.file_exists(file_name)

    def get_files_in_dir(self, file_dir) -> [str]:
        """
        Gets a list of filenames in the given dir
        Args:
            file_dir (): the directory

        Returns: list of filenames

        """

        sftp_client = self.ssh_connection.get_sftp_client()
        return sftp_client.listdir(file_dir)
