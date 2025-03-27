"""Software list keywords."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.upgrade.objects.software_list_output import SoftwareListOutput


class SoftwareListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the
    'software list' commands.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Instance of the class.

        Args:
            ssh_connection: An instance of an SSH connection.

        """
        self.ssh_connection = ssh_connection

    def get_software_list(self, sudo=False) -> SoftwareListOutput:
        """
        Get the software list.

        Args:
            sudo: True or False

        """
        if sudo:
            output = self.ssh_connection.send_as_sudo("software list")
        else:
            output = self.ssh_connection.send(source_openrc("software list"))
        self.validate_success_return_code(self.ssh_connection)
        software_list_output = SoftwareListOutput(output)

        return software_list_output
