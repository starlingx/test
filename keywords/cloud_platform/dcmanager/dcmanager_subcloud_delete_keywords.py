from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class DcManagerSubcloudDeleteKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud delete' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh for the active controller
        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_delete(self, subcloud_name: str):
        """
        Deletes the subcloud using 'dcmanager subcloud delete <subcloud name>'.

        Args:
            subcloud_name (str): a str representing a subcloud's name.
        """
        # Delete the subcloud
        self.ssh_connection.send(source_openrc(f"dcmanager subcloud delete {subcloud_name}"))
        self.validate_success_return_code(self.ssh_connection)
