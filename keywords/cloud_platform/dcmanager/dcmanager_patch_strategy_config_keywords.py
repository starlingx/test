from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_patch_strategy_config_output import (
    DcmanagerPatchStrategyConfigOutput,
)
from keywords.cloud_platform.dcmanager.objects.dcmanager_patch_strategy_config_show_output import (
    DcmanagerPatchStrategyConfigShowOutput,
)


class DcmanagerPatchStrategyConfigKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager patch-strategy-config' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initializes DcmanagerPatchStrategyConfigKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_patch_strategy_config_list(self) -> DcmanagerPatchStrategyConfigOutput:
        """
        Gets the dcmanager patch-strategy-config list.

        Returns:
            DcmanagerPatchStrategyConfigOutput: An object containing the list of patch strategy configs.
        """
        command = source_openrc("dcmanager patch-strategy-config list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPatchStrategyConfigOutput(output)

    def get_dcmanager_patch_strategy_config_show(self) -> DcmanagerPatchStrategyConfigShowOutput:
        """
        Gets the patch-strategy-config show.

        Returns:
            DcmanagerPatchStrategyConfigShowOutput: An object containing details of the patch strategy config.
        """
        command = source_openrc("dcmanager patch-strategy-config show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPatchStrategyConfigShowOutput(output)
