from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_prestage_strategy_show_output import DcmanagerPrestageStrategyShowOutput


class DcmanagerPrestageStrategyKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager prestage-strategy' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initializes DcmanagerPrestageStrategyKeywords.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection

    def get_dcmanager_prestage_strategy_create(self) -> DcmanagerPrestageStrategyShowOutput:
        """
        Gets the prestage-strategy create.

        Returns:
            DcmanagerPrestageStrategyShowOutput: The output of the prestage strategy.
        """
        command = source_openrc("dcmanager prestage-strategy create")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPrestageStrategyShowOutput(output)

    def get_dcmanager_prestage_strategy_show(self) -> DcmanagerPrestageStrategyShowOutput:
        """
        Gets the prestage-strategy show.

        Returns:
            DcmanagerPrestageStrategyShowOutput: An object containing details of the prestage strategy .
        """
        command = source_openrc("dcmanager prestage-strategy show")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPrestageStrategyShowOutput(output)

    def get_dcmanager_prestage_strategy_delete(self) -> DcmanagerPrestageStrategyShowOutput:
        """
        Gets the prestage-strategy delete.

        Returns:
            DcmanagerPrestageStrategyShowOutput: An object containing details of the prestage strategy .
        """
        command = source_openrc("dcmanager prestage-strategy delete")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return DcmanagerPrestageStrategyShowOutput(output)
