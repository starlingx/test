from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.datanetwork.objects.system_datanetwork_list_output import SystemDatanetworkListOutput


class SystemDatanetworkListKeywords(BaseKeyword):
    """
    Class for System datanetwork list keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def system_datanetwork_list(self) -> SystemDatanetworkListOutput:
        """
        Keyword for system datanetwork-list command
        Returns:

        """
        output = self.ssh_connection.send(source_openrc('system datanetwork-list'))
        self.validate_success_return_code(self.ssh_connection)
        system_datanetworks_output = SystemDatanetworkListOutput(output)
        return system_datanetworks_output
