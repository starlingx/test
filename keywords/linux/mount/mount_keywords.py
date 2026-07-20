from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class MountKeywords(BaseKeyword):
    """Keywords for Linux mount operations."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize MountKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to execute mount commands.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def remount_read_write(self, mount_point: str) -> None:
        """Remount a filesystem with read-write permissions.

        Args:
            mount_point (str): The mount point to remount (e.g., "/usr").
        """
        get_logger().log_info(f"Remounting {mount_point} with read-write permissions")
        self.ssh_connection.send_as_sudo(f"mount -o rw,remount {mount_point}")

    def get_mounts(self, filter_pattern: str = "") -> str:
        """Run mount and optionally filter output by a pattern.

        Args:
            filter_pattern (str): Optional pattern to grep for in mount output.
                If empty, returns all mounts.

        Returns:
            str: Mount output, optionally filtered by the pattern.
        """
        if filter_pattern:
            cmd = f"mount | grep {filter_pattern}"
        else:
            cmd = "mount"
        output = self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
        if isinstance(output, list):
            return "\n".join(output)
        return output
