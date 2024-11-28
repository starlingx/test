from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class TarKeywords(BaseKeyword):
    """
    Class for linux tar command keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def extract_tar_file(self, file_name: str):
        """
        Extracts the given tar file
        Args:
            file_name (): the name of the file

        Returns:

        """
        self.ssh_connection.send(f'tar -xzvf {file_name}')
        self.validate_success_return_code(self.ssh_connection)
