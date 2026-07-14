"""Software metapackage list keywords."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.upgrade.objects.software_metapackage_list_output import SoftwareMetapackageListOutput


class SoftwareMetapackageListKeywords(BaseKeyword):
    """Keywords for the 'software metapackage list' command.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """Initialize the keywords class.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def get_software_metapackage_list(self) -> SoftwareMetapackageListOutput:
        """Get the software metapackage list for all releases.

        Returns:
            SoftwareMetapackageListOutput: Parsed metapackage list output.
        """
        output = self.ssh_connection.send(source_openrc("software metapackage list --a"))
        self.validate_success_return_code(self.ssh_connection)
        return SoftwareMetapackageListOutput(output)
