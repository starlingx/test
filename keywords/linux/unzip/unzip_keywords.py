"""Linux unzip operations keywords."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class UnzipKeywords(BaseKeyword):
    """Linux unzip operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize unzip keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for command execution.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def unzip_file(self, zip_file: str, destination: str = None, overwrite: bool = True) -> None:
        """Extract zip file.

        Args:
            zip_file (str): Path to zip file to extract.
            destination (str): Optional destination directory.
            overwrite (bool): Overwrite existing files. Defaults to True.
        """
        cmd = "unzip"
        if overwrite:
            cmd += " -o"
        cmd += f" {zip_file}"
        if destination:
            cmd += f" -d {destination}"

        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
