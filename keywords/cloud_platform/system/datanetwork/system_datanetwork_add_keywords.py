from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SystemDatanetworkAddKeywords(BaseKeyword):
    """
    Class for System Datanetwork Add keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def datanetwork_add(self, datanetwork_name, datanetwork_type):
        """
        Adds the datanetwork
        Args:
            datanetwork_name (): the name for the datanetwork
            datanetwork_type (): the type of the datanetwork

        Returns:

        """
        self.ssh_connection.send(source_openrc(f"system datanetwork-add {datanetwork_name} {datanetwork_type}"))
        self.validate_success_return_code(self.ssh_connection)
