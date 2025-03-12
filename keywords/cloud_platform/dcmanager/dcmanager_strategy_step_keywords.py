from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_strategy_step_output import DcmanagerStrategyStepOutput
from keywords.cloud_platform.dcmanager.objects.dcmanager_strategy_step_show_output import DcmanagerStrategyStepShowOutput


class DcmanagerStrategyStepKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager strategy-step' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initializes DcmanagerStrategyStepKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_strategy_step_list(self) -> DcmanagerStrategyStepOutput:
        """
        Gets the dcmanager strategy-step list.

        Returns:
            DcmanagerStrategyStepOutput: An object containing the list of strategy steps.
        """
        command = source_openrc("dcmanager strategy-step list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerStrategyStepOutput(output)

    def get_dcmanager_strategy_step_show(self, subcloud_name: str) -> DcmanagerStrategyStepShowOutput:
        """
        Gets the dcmanager strategy-step show.

        Args:
            subcloud_name (str): The subcloud name.

        Returns:
            DcmanagerStrategyStepShowOutput: An object containing details of the strategy step.
        """
        command = source_openrc(f"dcmanager strategy-step show {subcloud_name}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerStrategyStepShowOutput(output)
