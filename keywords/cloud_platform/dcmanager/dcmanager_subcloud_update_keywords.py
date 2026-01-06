from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_show_output import DcManagerSubcloudShowOutput


class DcManagerSubcloudUpdateKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud update' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection): An active SSH connection to the controller.

        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_update(self, subcloud_name: str, update_attr: str, update_value: str) -> DcManagerSubcloudShowOutput:
        """
        Updates the subcloud attr using'dcmanager subcloud update <subcloud name> --<update_attr> <update_value>' output.

        Args:
            subcloud_name (str): a str representing a subcloud's name.
            update_attr (str): the attribute to update (ex. description)
            update_value (str): the value to update the attribute to (ex. this is a new description)

        Returns:
            DcManagerSubcloudShowOutput: Object representation of the command output.

        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud update {subcloud_name} --{update_attr} '{update_value}'"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_subcloud_show_output = DcManagerSubcloudShowOutput(output)

        return dcmanager_subcloud_show_output

    def dcmanager_subcloud_update_with_error(self, subcloud_name: str, update_attr: str, update_value: str) -> str:
        """
        Updates the subcloud attr using'dcmanager subcloud update <subcloud name> --<update_attr> <update_value>' output(error handling version).

        Args:
            subcloud_name (str): a str representing a subcloud's name.
            update_attr (str): the attribute to update (ex. description)
            update_value (str): the value to update the attribute to (ex. this is a new description)

        Returns:
            str: Raw command output (for error validation).

        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud update {subcloud_name} --{update_attr} '{update_value}'"))
        if isinstance(output, list) and len(output) > 0:
            return "\n".join(line.strip() for line in output)
        return output.strip() if isinstance(output, str) else str(output)
