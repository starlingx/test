from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.show.objects.system_show_output import SystemShowOutput


class SystemShowKeywords(BaseKeyword):
    """
    System Show Keywords class
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def system_show(self) -> SystemShowOutput:
        """
        Gets the output from the command system show
        """
        output = self.ssh_connection.send(source_openrc(f'system show'))
        self.validate_success_return_code(self.ssh_connection)
        system_show_output = SystemShowOutput(output)

        return system_show_output
