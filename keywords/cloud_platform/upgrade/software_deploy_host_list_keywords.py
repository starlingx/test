"""Software deploy host-list keywords."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.upgrade.objects.software_deploy_host_list_output import SoftwareDeployHostListOutput


class SoftwareDeployHostListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'software deploy host-list' command.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def get_software_deploy_host_list(self, sudo: bool = False) -> SoftwareDeployHostListOutput:
        """
        Get the software deploy host-list.

        Args:
            sudo (bool): Run command with sudo if True.

        Returns:
            SoftwareDeployHostListOutput: Parsed host-list output.
        """
        if sudo:
            output = self.ssh_connection.send_as_sudo("software deploy host-list")
        else:
            output = self.ssh_connection.send(source_openrc("software deploy host-list"))

        self.validate_success_return_code(self.ssh_connection)

        return SoftwareDeployHostListOutput(output)
