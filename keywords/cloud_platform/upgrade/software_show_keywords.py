from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.upgrade.objects.software_show_output import SoftwareShowOutput


class SoftwareShowKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the
    'software show <rel-id>' commands.

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

    def get_software_show(self, sudo=False, release_id=None) -> SoftwareShowOutput:
        """
        Get the software show.

        Args:
            sudo: True or False
            release_id: Release Name
        """
        if sudo:
            output = self.ssh_connection.send_as_sudo(f"software show {release_id}")
        else:
            output = self.ssh_connection.send(source_openrc(f"software show {release_id}"))
        self.validate_success_return_code(self.ssh_connection)
        software_show_output = SoftwareShowOutput(output)

        return software_show_output

    def get_release_state(self, release_id: str) -> str:
        """
        Return the release state of a specific version using 'software show'.

        Args:
            release_id (str): The software release ID to show.

        Returns:
            str: The state string (e.g., "available", "deployed", etc.)
        """
        output = self.get_software_show(sudo=True, release_id=release_id)
        return output.get_property_value("State")
