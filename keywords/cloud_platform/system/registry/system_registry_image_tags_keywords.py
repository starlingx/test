from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.registry.objects.system_registry_image_tags_output import SystemRegistryImageTagsOutput


class SystemRegistryImageTagsKeywords(BaseKeyword):
    """Keywords for the 'system registry-image-tags <image>' command.

    The command lists all tags for a specific image in the StarlingX local registry.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_image_tags(self, image_name: str, command_timeout: int = 60) -> SystemRegistryImageTagsOutput:
        """Run 'system registry-image-tags <image>' and return the parsed output.

        Args:
            image_name (str): Full image name to look up tags for.
            command_timeout (int): Seconds to wait for the command to complete (default 60).

        Returns:
            SystemRegistryImageTagsOutput: Parsed output containing all tags for the image.
        """
        get_logger().log_info(f"Getting registry tags for: {image_name}")
        output = self.ssh_connection.send(
            source_openrc(f"system registry-image-tags {image_name}"),
            command_timeout=command_timeout,
        )
        self.validate_success_return_code(self.ssh_connection)
        return SystemRegistryImageTagsOutput(output)
