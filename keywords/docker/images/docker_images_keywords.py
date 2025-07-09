from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.docker.images.object.docker_images_output import DockerImagesOutput


class DockerImagesKeywords(BaseKeyword):
    """
    Keywords for docker images
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): Active SSH connection to the system under test.
        """
        self.ssh_connection = ssh_connection

    def list_images(self) -> list[DockerImagesOutput]:
        """
        Lists docker images.

        Returns:
            list[DockerImagesOutput]: List of DockerImagesOutput objects representing the images
        """
        output = self.ssh_connection.send_as_sudo("docker images")
        docker_images = DockerImagesOutput(output).get_images()
        return docker_images

    def remove_image(self, image: str) -> None:
        """
        Removes the docker image.

        Args:
            image (str): the docker image to remove
        """
        output = self.ssh_connection.send_as_sudo(f"docker image rm {image}")

        # both the Untagged Image and no such images messages are valid
        assert len(list(filter(lambda output_line: f"Untagged: {image}" in output_line, output))) > 0 or len(list(filter(lambda output_line: f"Error: No such image: {image}" in output_line, output))) > 0

    def pull_image(self, image: str) -> None:
        """
        Pulls the image.

        Args:
            image (str): the image to pull
        """
        self.ssh_connection.send_as_sudo(f"docker image pull {image}")

    def prune_dangling_images(self) -> None:
        """
        Prunes all dangling Docker images to free disk space.
        """
        self.ssh_connection.send_as_sudo("docker image prune -f")
