import os
import shlex
from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


class TarKeywords(BaseKeyword):
    """
    Class for linux tar command keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize tar keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for file operations.
        """
        super().__init__()
        self.ssh_connection = ssh_connection
        self.file_ops = FileKeywords(ssh_connection)

    def extract_tar_file(self, file_name: str) -> None:
        """
        Extracts the given tar file.

        Args:
            file_name (str): the name of the file.
        """
        self.ssh_connection.send(f"tar -xzvf {file_name}")
        self.validate_success_return_code(self.ssh_connection)

    def decompress_tar_gz(self, file_name: str) -> None:
        """
        Decompresses a .tar.gz file into a .tar file without extracting contents.

        Args:
            file_name (str): The path to the .tar.gz file.

        Raises:
            ValueError: If the file does not have a .tar.gz extension.
        """
        if not file_name.endswith(".tar.gz"):
            raise ValueError("File must be a .tar.gz archive.")

        self.ssh_connection.send(f"gunzip -f {file_name}")

    def extract_tar_archive(self, tar_path: str, extract_to: Optional[str] = None) -> str:
        """Extract tar.gz archive to specified directory.

        Args:
            tar_path (str): Path to tar.gz archive file.
            extract_to (Optional[str]): Directory to extract to. Defaults to same directory as tar file.

        Returns:
            str: Path to extracted directory.
        """
        safe_tar_path = shlex.quote(tar_path)

        # Verify tar file exists and has valid extension
        if not self.file_ops.file_exists(tar_path):
            raise FileNotFoundError(f"Tar file not found: {tar_path}")

        if not (tar_path.endswith(".tar.gz") or tar_path.endswith(".tgz")):
            raise ValueError("File must be a .tar.gz or .tgz archive.")

        # Determine extraction directory and command
        if extract_to is None:
            if tar_path.endswith(".tar.gz"):
                extract_dir = tar_path.replace(".tar.gz", "")
            else:  # .tgz
                extract_dir = tar_path.replace(".tgz", "")
            dir_path = shlex.quote(os.path.dirname(tar_path))
            file_name = shlex.quote(os.path.basename(tar_path))
            extract_cmd = f"cd {dir_path} && tar -xzf {file_name}"
        else:
            extract_dir = extract_to
            safe_extract_dir = shlex.quote(extract_dir)
            self.file_ops.create_directory(safe_extract_dir)
            extract_cmd = f"tar -xzf {safe_tar_path} -C {safe_extract_dir}"

        get_logger().log_info(f"Extracting {tar_path} to {extract_dir}")
        self.ssh_connection.send(extract_cmd)
        self.validate_success_return_code(self.ssh_connection)

        get_logger().log_info(f"Archive extracted successfully to {extract_dir}")
        return extract_dir
