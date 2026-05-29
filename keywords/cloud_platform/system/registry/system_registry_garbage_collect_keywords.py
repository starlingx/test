from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SystemRegistryGarbageCollectKeywords(BaseKeyword):
    """Keywords for the 'system registry-garbage-collect' command.

    The command reclaims storage from images previously marked for deletion via
    'system registry-image-delete'. Run after image deletes to actually free disk.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def run_garbage_collect(self, command_timeout: int = 300) -> None:
        """Run 'system registry-garbage-collect' to reclaim registry storage.

        Validates the command's return code, so a failed garbage collect raises
        an exception instead of silently returning.

        Args:
            command_timeout (int): Seconds to wait for the command to complete (default 300).
        """
        get_logger().log_info("Running system registry garbage collect")
        self.ssh_connection.send(
            source_openrc("system registry-garbage-collect"),
            command_timeout=command_timeout,
        )
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Registry garbage collection completed")
