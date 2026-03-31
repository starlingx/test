import re

from config.docker.objects.registry import Registry
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords
from keywords.docker.push.docker_push_keywords import DockerPushKeywords


class DockerLoadImageKeywords(BaseKeyword):
    """
    Keywords for Loading images into docker registry
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize DockerLoadImageKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def load_docker_image_to_host(self, image_file_name: str) -> str:
        """Load a docker image from a tar file on the host.

        Args:
            image_file_name (str): The image file name.

        Returns:
            str: The loaded image name.

        """
        output = self.ssh_connection.send_as_sudo(f"docker load -i {image_file_name}")
        string_output = "".join(output)
        validate_str_contains(string_output, "Loaded image", "Image")

        for line in output:
            match = re.search(r"Loaded image:\s*(\S+)", line)
            if match:
                return match.group(1)

    def tag_docker_image_for_registry(self, image_name: str, tag_name: str, registry: Registry):
        """Tag a docker image for a registry.

        Args:
            image_name (str): The image name.
            tag_name (str): The tag name.
            registry (Registry): The registry configuration object.

        Raises:
            Exception: If the docker tag command fails.

        """
        output = self.ssh_connection.send_as_sudo(f"docker tag {image_name} {registry.get_registry_url()}/{tag_name}")
        if len(output) > 1:  # If things go well, we get the prompt back. Otherwise, the first line returned is an Error.
            get_logger().log_error(output[0])
            raise Exception(f"Failed to tag docker image {image_name}")

    def push_docker_image_to_registry(self, tag_name: str, registry: Registry):
        """Pushes the docker image to the registry.

        Logs in to the registry and pushes the tagged image. Uses DockerPushKeywords
        to ensure the push completes before returning.

        Args:
            tag_name (str): The tag name for the image.
            registry (Registry): The registry configuration object.

        """
        DockerLoginKeywords(self.ssh_connection).login(registry.get_user_name(), registry.get_password(), registry.get_registry_url())
        DockerPushKeywords(self.ssh_connection).push(f"{registry.get_registry_url()}/{tag_name}")
