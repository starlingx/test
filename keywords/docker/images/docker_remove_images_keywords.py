from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class DockerRemoveImagesKeywords(BaseKeyword):
    """
    Class for Docker Remove Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def remove_docker_image(self, docker_image: str):
        """
        Removes the docker image
        Args:
            docker_image (): the docker image to remove

        Returns:

        """
        self.ssh_connection.send_as_sudo(f'docker rmi {docker_image}')
