from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SystemRegistryImageDeleteKeywords(BaseKeyword):
    """Keywords for the 'system registry-image-delete <image:tag>' command.

    The command deletes a specific image:tag from the StarlingX local registry.
    Use 'system registry-garbage-collect' afterwards to actually reclaim storage.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def delete_registry_image(self, image_name: str, tag: str, command_timeout: int = 60) -> None:
        """Run 'system registry-image-delete <image>:<tag>'.

        Validates the command's return code, so a failed delete raises an
        exception instead of silently returning.

        Args:
            image_name (str): Full image name.
            tag (str): Tag of the image to delete.
            command_timeout (int): Seconds to wait for the command to complete (default 60).
        """
        image_ref = f"{image_name}:{tag}"
        get_logger().log_info(f"Deleting registry image: {image_ref}")
        self.ssh_connection.send(
            source_openrc(f"system registry-image-delete {image_ref}"),
            command_timeout=command_timeout,
        )
        self.validate_success_return_code(self.ssh_connection)
