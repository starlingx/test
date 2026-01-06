import math
import shlex
import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
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

    def create_file_with_echo(self, file_name: str, content: str) -> bool:
        """
        Creates a file based on its content with the echo command.

        Args:
            file_name (str): the file name.
            content (str): content to be added in the file.

        Returns:
            bool: True if create successful, False otherwise.
        """
        self.ssh_connection.send(f"echo '{content}' > {file_name}")
        return self.file_exists(file_name)

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

    def delete_directory(self, directory_path: str) -> bool:
        """Remove directory and all its contents.

        Args:
            directory_path (str): Directory path to remove.

        Returns:
            bool: True if delete successful, False otherwise.
        """
        cleanup_cmd = f"rm -rf {shlex.quote(directory_path)}"
        self.ssh_connection.send(cleanup_cmd)
        return not self.file_exists(directory_path)

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
            grep_pattern (str): the pattern to use to filter lines ex. 'ptp4l\\|phc2sys'.

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

    def read_file(self, file_path: str) -> list[str]:
        """
        Read the contents of a file.

        Args:
            file_path (str): The absolute path to the file.

        Returns:
            list[str]: The lines of the file.
        """
        return self.ssh_connection.send(f"cat {file_path}")

    def find_in_tgz(self, file_path: str, grep_pattern: str) -> int:
        """
        Searches for a string in tgz file

        Args:
            file_path (str): The absolute path to the file.
            grep_pattern (str): Pattern to be searched.

        Returns:
            int: Number of matches found.
        """
        matches = int(self.ssh_connection.send(f"tar -tf {file_path} | grep {grep_pattern} | wc -l")[0].strip("\n"))
        return matches

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

    def concatenate_files_with_sudo(self, file1_path: str, file2_path: str, output_path: str) -> bool:
        """
        Concatenate two files and store the result in a specified location using sudo.

        Args:
            file1_path (str): Path to the first file.
            file2_path (str): Path to the second file.
            output_path (str): Path where the concatenated result should be stored.

        Returns:
            bool: True if concatenation is successful, False otherwise.

        Raises:
            KeywordException: If there is an error executing the command.
        """
        try:
            cmd = f"cat {file1_path} {file2_path} > {output_path}"
            self.ssh_connection.send_as_sudo(cmd)
            return self.validate_file_exists_with_sudo(output_path)
        except Exception as e:
            get_logger().log_error(f"Failed to concatenate files {file1_path} and {file2_path} to {output_path}: {e}")
            raise KeywordException(f"Failed to concatenate files {file1_path} and {file2_path} to {output_path}: {e}")

    def create_directory(self, dir_path: str) -> bool:
        """
        Create a directory if it does not already exist (non-sudo).

        Args:
            dir_path (str): Absolute path to the directory to create.

        Returns:
            bool: True if directory exists or was created successfully.
        """
        if self.file_exists(dir_path):
            get_logger().log_info(f"Directory already exists: {dir_path}")
            return True

        self.ssh_connection.send(f"mkdir -p {dir_path}")
        return self.file_exists(dir_path)

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

    def rename_file(self, old_file_name: str, new_file_name: str):
        """
        Renames the file.

        Args:
            old_file_name (str): path to file to be renamed
            new_file_name (str): path to be set for renamed file
        """
        self.ssh_connection.send_as_sudo(f"mv {old_file_name} {new_file_name}")

    def move_file(self, source: str, destination: str, sudo: bool = False) -> None:
        """
        Move file or directory from source to destination.

        Args:
            source (str): Source file or directory path.
            destination (str): Destination file or directory path.
            sudo (bool): Whether to use sudo privileges. Defaults to False.
        """
        if sudo:
            self.ssh_connection.send_as_sudo(f"mv {source} {destination}")
        else:
            self.ssh_connection.send(f"mv {source} {destination}")
        self.validate_success_return_code(self.ssh_connection)

    def rsync_to_remote_server(self, local_dest_path: str, remote_server: str, remote_user: str, remote_password: str, remote_path: str, recursive: bool = False, rsync_options: str = "") -> None:
        """
        Rsync a file or directory to a remote server from the target host.

        This method runs rsync on the host associated with the current SSHConnection
        (self.ssh_connection). It initiates an outbound connection to the remote server
        using sshpass for authentication, allowing flexible copying of files or directories
        to external sources from the target host.

        Default rsync options are '-avz' (archive mode, verbose, compression). Additional options
        can be appended if needed to support scenarios like progress display, bandwidth throttling, or cleanup.

        Args:
            local_dest_path (str): Absolute path on the target host where the file or directory should be copied.
            remote_server (str): Remote server IP address or hostname.
            remote_user (str): Username to authenticate with the remote server.
            remote_password (str): Password to authenticate with the remote server.
            remote_path (str): Absolute path to the file or directory on the remote server.
            recursive (bool, optional): Whether to copy directories recursively by adding 'r' to options. Defaults to False.
            rsync_options (str, optional): Additional rsync command-line options (e.g., "--progress", "--bwlimit=10000"). Defaults to "".

        Raises:
            KeywordException: If the rsync operation fails due to SSH, rsync, or connection issues.
        """
        opts = "-avz"
        if recursive:
            opts += "r"

        if rsync_options:
            opts += f" {rsync_options}"

        # Handle IPv6 addresses by wrapping them in brackets
        if ":" in remote_server and not remote_server.startswith("["):
            remote_server = f"[{remote_server}]"

        cmd = f"sshpass -p '{remote_password}' rsync {opts} -e 'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10' {local_dest_path} {remote_user}@{remote_server}:{remote_path}"

        get_logger().log_info(f"Executing rsync command: {cmd}")

        try:
            self.ssh_connection.send(cmd)
            self.validate_success_return_code(self.ssh_connection)
        except Exception as e:
            get_logger().log_error(f"Failed to rsync file from {local_dest_path} to {remote_user}@{remote_server}:{remote_path}: {e}")
            raise KeywordException(f"Failed to rsync file from {local_dest_path} to {remote_user}@{remote_server}:{remote_path}: {e}") from e

    def rsync_from_remote_server(self, remote_server: str, remote_user: str, remote_password: str, remote_path: str, local_dest_path: str, recursive: bool = False, rsync_options: str = "") -> None:
        """
        Rsync a file or directory from a remote server to the target host.

        This method runs rsync on the host associated with the current SSHConnection
        (self.ssh_connection). It initiates an outbound connection to the remote server
        using sshpass for authentication, allowing flexible copying of files or directories
        from external sources to the target host.

        Default rsync options are '-avz' (archive mode, verbose, compression). Additional options
        can be appended if needed to support scenarios like progress display, bandwidth throttling, or cleanup.

        Args:
            remote_server (str): Remote server IP address or hostname.
            remote_user (str): Username to authenticate with the remote server.
            remote_password (str): Password to authenticate with the remote server.
            remote_path (str): Absolute path to the file or directory on the remote server.
            local_dest_path (str): Absolute path on the target host where the file or directory should be copied.
            recursive (bool, optional): Whether to copy directories recursively by adding 'r' to options. Defaults to False.
            rsync_options (str, optional): Additional rsync command-line options (e.g., "--progress", "--bwlimit=10000"). Defaults to "".

        Raises:
            KeywordException: If the rsync operation fails due to SSH, rsync, or connection issues.
        """
        opts = "-avz"
        if recursive:
            opts += "r"

        if rsync_options:
            opts += f" {rsync_options}"

        # Handle IPv6 addresses by wrapping them in brackets
        if ":" in remote_server and not remote_server.startswith("["):
            remote_server = f"[{remote_server}]"

        cmd = f"sshpass -p '{remote_password}' rsync {opts} -e 'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10' {remote_user}@{remote_server}:{remote_path} {local_dest_path}"

        get_logger().log_info(f"Executing rsync command: {cmd}")

        try:
            self.ssh_connection.send(cmd)
            self.validate_success_return_code(self.ssh_connection)
        except Exception as e:
            get_logger().log_error(f"Failed to rsync file from {remote_user}@{remote_server}:{remote_path} to {local_dest_path}: {e}")
            raise KeywordException(f"Failed to rsync file from {remote_user}@{remote_server}:{remote_path} to {local_dest_path}: {e}") from e

        return True

    def copy_file(self, src_file: str, dest_file: str):
        """Copies a file from the source path to the destination path.

        Args:
            src_file  (str): The source file path.
            dest_file (str): The destination file path.
        """
        self.ssh_connection.send(f"cp {src_file} {dest_file}")

    def make_executable(self, file_path: str) -> None:
        """Make file executable.

        Args:
            file_path (str): Path to file to make executable.
        """
        self.ssh_connection.send(f"chmod +x {file_path}")
        self.validate_success_return_code(self.ssh_connection)

    def create_file_to_fill_disk_space(self, dest_dir: str = "/opt/dc-vault") -> str:
        """Creates a file with the available space of the desired directory.

        Args:
            dest_dir (str): Directory where the file is created. Default to home dir.

        Returns:
            str: Created file path.
        """
        get_space_cmd = f"echo $(($(stat -f --format=\"%a*%S\" {dest_dir})))| awk '{{print $1 / (1024*1024*1024) }}'"
        available_space = self.ssh_connection.send_as_sudo(get_space_cmd)[0].strip("\n")
        rounded_size = math.ceil(float(available_space))
        file_size_to_be_created = math.trunc(1023 * float(rounded_size))

        get_logger().log_info(f"Creating file 'test' with size {file_size_to_be_created}.")
        self.ssh_connection.send_as_sudo(f"dd if=/dev/zero of={dest_dir}/giant_test_file bs=1M count={file_size_to_be_created}")
        remaining_space = self.ssh_connection.send_as_sudo(get_space_cmd)[0].strip("\n")
        remaining_space = math.trunc(float(remaining_space))
        validate_equals(remaining_space, 0, "Validate that the remaining space on local is 0.")
        path_to_file = f"{dest_dir}/giant_test_file"
        return path_to_file
