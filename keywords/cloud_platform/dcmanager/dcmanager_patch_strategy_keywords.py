from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_patch_strategy_show_output import DcmanagerPatchStrategyShowOutput


class DcmanagerPatchStrategyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager patch-strategy' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initializes DcmanagerPatchStrategyKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_patch_strategy_show(self) -> DcmanagerPatchStrategyShowOutput:
        """
        Gets the patch-strategy show.

        Returns:
            DcmanagerPatchStrategyShowOutput: An object containing details of the patch strategy .
        """
        command = source_openrc("dcmanager patch-strategy show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPatchStrategyShowOutput(output)

    def get_dcmanager_patch_strategy_create(self) -> DcmanagerPatchStrategyShowOutput:
        """
        Gets the patch-strategy create.

        Returns:
            DcmanagerPatchStrategyShowOutput: An object containing details of the patch strategy .
        """
        command = source_openrc("dcmanager patch-strategy create")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPatchStrategyShowOutput(output)

    def get_dcmanager_patch_strategy_delete(self) -> DcmanagerPatchStrategyShowOutput:
        """
        Gets the patch-strategy delete.

        Returns:
            DcmanagerPatchStrategyShowOutput: An object containing details of the patch strategy .
        """
        command = source_openrc("dcmanager patch-strategy delete")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPatchStrategyShowOutput(output)
