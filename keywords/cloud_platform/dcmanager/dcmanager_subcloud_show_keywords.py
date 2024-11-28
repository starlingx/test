from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_show_output import DcManagerSubcloudShowOutput


class DcManagerSubcloudShowKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud show' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:

        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_show(self, subcloud_name: str) -> DcManagerSubcloudShowOutput:
        """
        Gets the 'dcmanager subcloud show <subcloud name>' output.
        Args: subcloud_name (str): a str representing na subcloud's name.

        Returns:
            dcmanager subcloud show (DcManagerSubcloudShowOutput): a DcManagerSubcloudShowOutput object representing the
            output of the command 'dcmanager subcloud show <subcloud name>'.

        """
        output = self.ssh_connection.send(source_openrc(f'dcmanager subcloud show {subcloud_name}'))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_subcloud_show_output = DcManagerSubcloudShowOutput(output)

        return dcmanager_subcloud_show_output
