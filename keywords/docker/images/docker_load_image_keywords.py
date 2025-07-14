from config.docker.objects.registry import Registry
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords


class DockerLoadImageKeywords(BaseKeyword):
    """
    Keywords for Loading images into docker registry
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def load_docker_image_to_host(self, image_file_name: str):
        """
        Keyword to load the docker to host
        Args:
            image_file_name (): the image file name

        Returns:

        """
        output = self.ssh_connection.send_as_sudo(f"docker load -i {image_file_name}")
        string_output = "".join(output)
        validate_str_contains(string_output, "Loaded image", "Image")

    def tag_docker_image_for_registry(self, image_name: str, tag_name: str, registry: Registry):
        """
        Tags the docker image for the registry
        Args:
            image_name (): the image name
            tag_name (): the tag name
            registry (): the registry

        Returns:

        """
        output = self.ssh_connection.send_as_sudo(f"docker tag {image_name} {registry.get_registry_url()}/{tag_name}")
        if len(output) > 1: # If things go well, we get the prompt back. Otherwise, the first line returned is an Error.
            get_logger().log_error(output[0])
            raise Exception(f"Failed to tag docker image {image_name}")


    def push_docker_image_to_registry(self, tag_name: str, registry: Registry):
        """
        Pushes the docker image to the registry
        Args:
            tag_name (): the tag name
            registry (): the registry

        Returns:

        """
        DockerLoginKeywords(self.ssh_connection).login(registry.get_user_name(), registry.get_password(), registry.get_registry_url())
        self.ssh_connection.send_as_sudo(f'docker push {registry.get_registry_url()}/{tag_name}')
