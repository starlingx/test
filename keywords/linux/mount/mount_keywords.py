from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection


class MountKeywords:
    """Keywords for Linux mount operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize MountKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to execute mount commands.
        """
        self.ssh_connection = ssh_connection

    def remount_read_write(self, mount_point: str) -> None:
        """
        Remount a filesystem with read-write permissions.

        Args:
            mount_point (str): The mount point to remount (e.g., "/usr").
        """
        get_logger().log_info(f"Remounting {mount_point} with read-write permissions")
        self.ssh_connection.send_as_sudo(f"mount -o rw,remount {mount_point}")
