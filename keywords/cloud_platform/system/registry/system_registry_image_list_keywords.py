from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.registry.objects.system_registry_image_list_output import SystemRegistryImageListOutput


class SystemRegistryImageListKeywords(BaseKeyword):
    """Keywords for the 'system registry-image-list' command.

    The command lists all container images in the StarlingX local registry.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_registry_image_list(self, command_timeout: int = 120) -> SystemRegistryImageListOutput:
        """Run 'system registry-image-list' and return the parsed output.

        Args:
            command_timeout (int): Seconds to wait for the command to complete (default 120).

        Returns:
            SystemRegistryImageListOutput: Parsed output containing all images
            currently in the local registry.
        """
        get_logger().log_info("Getting system registry image list")
        output = self.ssh_connection.send(
            source_openrc("system registry-image-list"),
            command_timeout=command_timeout,
        )
        self.validate_success_return_code(self.ssh_connection)
        return SystemRegistryImageListOutput(output)
