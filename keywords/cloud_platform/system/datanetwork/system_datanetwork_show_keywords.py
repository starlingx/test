from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.datanetwork.objects.system_datanetwork_show_output import SystemDatanetworkShowOutput


class SystemDatanetworkShowKeywords(BaseKeyword):
    """
    Contains methods to interact with system datanetwork using an SSH connection.

    Args:
        ssh_connection (SSHConnection): An instance of an SSH connection.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initializes the SystemDatanetworkShowKeywords with an SSH connection.

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def system_datanetwork_show(self, datanetwork_id: str) -> SystemDatanetworkShowOutput:
        """
        Retrieves information about a specific datanetwork.

        Args:
            datanetwork_id (str): The identifier of the datanetwork.

        Returns:
            SystemDatanetworkShowOutput: An output object containing details about the datanetwork.

        Raises:
            SomeException: Description of any specific exception(s) that might be raised.
        """
        output = self.ssh_connection.send(source_openrc(f'system datanetwork-show {datanetwork_id}'))
        self.validate_success_return_code(self.ssh_connection)
        system_datanetwork_output = SystemDatanetworkShowOutput(output)
        return system_datanetwork_output
