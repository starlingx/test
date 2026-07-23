from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class DockerLoginKeywords(BaseKeyword):
    """Class for Docker login keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize DockerLoginKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def login(self, user_name: str, password: str, registry_name: str):
        """Log in to a docker registry.

        Args:
            user_name (str): the registry user name.
            password (str): the registry password.
            registry_name (str): the registry name.
        """
        self.ssh_connection.send_as_sudo(f"docker login -u '{user_name}' -p '{password}' '{registry_name}'")
