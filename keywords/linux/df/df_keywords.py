"""Linux df command keywords."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.df.df_output import DfOutput


class DfKeywords(BaseKeyword):
    """Linux df command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize df keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to target host.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def get_disk_usage(self, path: str = "/") -> DfOutput:
        """Get disk usage information for specified path.

        Args:
            path (str): Filesystem path to check. Defaults to "/".

        Returns:
            DfOutput: Disk usage information collection.
        """
        # Execute df command via SSH and get raw output
        raw_result = self.ssh_connection.send(f"df {path}")
        # Parse output and return collection of df objects
        return DfOutput(raw_result)

    def allocate_disk_space(self, size_gb: int, file_path: str):
        """Allocate disk space using fallocate command.

        Args:
            size_gb (int): Size in gigabytes to allocate.
            file_path (str): Path where to create the allocation file.
        """
        get_logger().log_info(f"Allocating {size_gb}G disk space to {file_path}")
        self.ssh_connection.send(f"fallocate -l {size_gb}G {file_path}")
