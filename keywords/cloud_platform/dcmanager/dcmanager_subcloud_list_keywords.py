from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_output import DcManagerSubcloudListOutput


class DcManagerSubcloudListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud list' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:

        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_list(self) -> DcManagerSubcloudListOutput:
        """
        Gets the 'dcmanager subcloud list' output.
        Args: None

        Returns:
            dcmanager subcloud list (DcManagerSubcloudListOutput): a DcManagerSubcloudListOutput object representing
            the output of the command 'dcmanager subcloud list'.

        """
        output = self.ssh_connection.send(source_openrc('dcmanager subcloud list'))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_subcloud_list_output = DcManagerSubcloudListOutput(output)

        return dcmanager_subcloud_list_output
