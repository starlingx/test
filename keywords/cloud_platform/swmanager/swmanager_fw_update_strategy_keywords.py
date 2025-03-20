from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.swmanager.objects.swmanager_fw_update_strategy_show_output import SwmanagerFwUpdateStrategyShowOutput


class SwmanagerFwUpdateStrategyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'sw-manager fw-update-strategy' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initializes SwmanagerFwUpdateStrategyKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_swmanager_fw_update_strategy_show(self) -> SwmanagerFwUpdateStrategyShowOutput:
        """
        Gets the sw-manager fw-update-strategy show.

        Returns:
            SwmanagerFwUpdateStrategyShowOutput: An object containing details of the fw_update_strategy.
        """
        command = source_openrc("sw-manager fw-update-strategy show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SwmanagerFwUpdateStrategyShowOutput(output)
