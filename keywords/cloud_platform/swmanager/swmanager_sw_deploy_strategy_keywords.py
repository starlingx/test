from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_show_output import SwManagerSwDeployStrategyShowOutput


class SwmanagerSwDeployStrategyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'sw-manager sw-deploy-strategy' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initializes SwmanagerSwDeployStrategyKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_sw_deploy_strategy_abort(self):
        """Gets the sw-deploy-strategy abort."""
        command = source_openrc("sw-manager sw-deploy-strategy abort")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def get_sw_deploy_strategy_apply(self):
        """Gets the sw-deploy-strategy apply."""
        command = source_openrc("sw-manager sw-deploy-strategy apply")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def get_sw_deploy_strategy_create(self, release: str, delete: bool) -> SwManagerSwDeployStrategyShowOutput:
        """Gets the sw-deploy-strategy create.

        Args:
            release (str): The release to be used for the strategy.
            delete (bool): If True, pass --delete as an argument to the command.

        Returns:
            SwManagerSwDeployStrategyShowOutput: The output of the prestage strategy.
        """
        if delete:
            delete_arg = "--delete"
        else:
            delete_arg = ""

        command = source_openrc(f"sw-manager sw-deploy-strategy create {delete_arg} {release}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SwManagerSwDeployStrategyShowOutput(output)

    def get_sw_deploy_strategy_show(self) -> SwManagerSwDeployStrategyShowOutput:
        """Gets the sw-deploy-strategy show.

        Returns:
            SwManagerSwDeployStrategyShowOutput: An object containing details of the prestage strategy .
        """
        command = source_openrc("sw-manager sw-deploy-strategy show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SwManagerSwDeployStrategyShowOutput(output)

    def get_sw_deploy_strategy_delete(self) -> None:
        """Gets the sw-deploy-strategy delete.

        Returns:
            None: None.
        """
        command = source_openrc("sw-manager sw-deploy-strategy delete")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return output
