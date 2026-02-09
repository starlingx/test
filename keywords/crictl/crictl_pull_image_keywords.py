from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class CrictlPullImageKeywords(BaseKeyword):
    """
    Class for crictl pull keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def crictl_pull_image(self, credentials: str, image_name: str) -> None:
        """
        Pull an image from a registry

        Args:
            credentials (str): credentials for accessing the registry USERNAME[:PASSWORD]
            image_name (str): image name NAME[:TAG]

        """
        self.ssh_connection.send_as_sudo(f"crictl pull --creds '{credentials}' {image_name}")
        self.validate_success_return_code(self.ssh_connection)
