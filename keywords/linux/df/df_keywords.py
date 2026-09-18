"""Linux df command keywords."""

import shlex

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

    def allocate_disk_space(self, size_gb: int, file_path: str, is_sudo: bool = False) -> None:
        """Allocate disk space using fallocate command.

        Args:
            size_gb (int): Size in gigabytes to allocate.
            file_path (str): Path where to create the allocation file.
            is_sudo (bool): Run fallocate with sudo (needed for root-owned dirs). Defaults to False.
        """
        get_logger().log_info(f"Allocating {size_gb}G disk space to {file_path}")
        command = f"fallocate -l {int(size_gb)}G {shlex.quote(file_path)}"
        if is_sudo:
            self.ssh_connection.send_as_sudo(command)
        else:
            self.ssh_connection.send(command)

    def allocate_disk_space_kb(self, size_kb: int, file_path: str, is_sudo: bool = False) -> None:
        """Allocate disk space with kilobyte precision using fallocate.

        This is used when the required filler size is computed dynamically from
        live ``df``/``du`` output and needs to be more precise than whole gigabytes.

        Args:
            size_kb (int): Size in kilobytes to allocate.
            file_path (str): Path where to create the allocation file.
            is_sudo (bool): Run fallocate with sudo (needed for root-owned dirs). Defaults to False.
        """
        get_logger().log_info(f"Allocating {size_kb}KiB disk space to {file_path}")
        command = f"fallocate -l {int(size_kb)}KiB {shlex.quote(file_path)}"
        if is_sudo:
            self.ssh_connection.send_as_sudo(command)
        else:
            self.ssh_connection.send(command)
