from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class TarKeywords(BaseKeyword):
    """
    Class for linux tar command keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

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
        self.validate_success_return_code(self.ssh_connection)
