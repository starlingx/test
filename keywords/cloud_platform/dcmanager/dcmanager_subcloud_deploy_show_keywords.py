from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_deploy_show_output import DcManagerSubcloudDeployShowOutput


class DcManagerSubcloudDeployShowKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'dcmanager subcloud deploy show' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_subcloud_deploy_show(self) -> DcManagerSubcloudDeployShowOutput:
        """Gets the 'dcmanager subcloud deploy show' output.

        Returns:
            DcManagerSubcloudDeployShowOutput: A DcManagerSubcloudDeployShowOutput object representing the
            output of the command 'dcmanager subcloud deploy show'.
        """
        output = self.ssh_connection.send(source_openrc("dcmanager subcloud deploy show"))
        self.validate_success_return_code(self.ssh_connection)
        return DcManagerSubcloudDeployShowOutput(output)