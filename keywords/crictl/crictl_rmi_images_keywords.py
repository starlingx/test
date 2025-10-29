from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class CrictlRmiImagesKeywords(BaseKeyword):
    """
    Class for crictl rmi keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def crictl_rmi_images(self, image_id: str) -> None:
        """
        Remove image

        Args:
            image_id (str): image id

        """
        self.ssh_connection.send_as_sudo(f"crictl rmi {image_id}")
        self.validate_success_return_code(self.ssh_connection)
