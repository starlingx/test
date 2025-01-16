from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_show_output import DcManagerSubcloudShowOutput


class DcManagerSubcloudUpdateKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud update' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:

        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_update(self, subcloud_name: str, update_attr: str, update_value: str) -> DcManagerSubcloudShowOutput:
        """
        Updates the subcloud attr using'dcmanager subcloud update <subcloud name> --<update_attr> <update_value>' output.
        Args: subcloud_name (str): a str representing a subcloud's name.
              update_attr (str): the attribute to update (ex. description)
              update_value (str): the value to update the attribute to (ex. this is a new description)

        Returns: DcManagerSubcloudShowOutput

        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud update {subcloud_name} --{update_attr} '{update_value}'"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_subcloud_show_output = DcManagerSubcloudShowOutput(output)

        return dcmanager_subcloud_show_output
