from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc

class SystemInterfaceNetworkKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system addrpool' commands.
    """


    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh for active controller.
        """
        self.ssh_connection = ssh_connection

    def interface_network_assign(self, hostname: str, interface_name: str, network_name: str) -> None:
        """
        Assign interface to network

        Args:
            hostname (str): The hostname
            interface_name (str): The interface name
            network_name (str): The network name
        """
        self.ssh_connection.send(
            source_openrc(f'system interface-network-assign {hostname} {interface_name} {network_name}'))
        self.validate_success_return_code(self.ssh_connection)
