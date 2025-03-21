from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword


class PTPConnectionKeywords(BaseKeyword):
    """
    Class to hold PTP connection keywords
    """

    def get_gnss_server_ssh(self) -> SSHConnection:
        """
        Gets the gnss server ssh

        Returns:
            SSHConnection: the ssh for the gnss server
        """
        ptp_config = ConfigurationManager.get_ptp_config()

        connection = SSHConnectionManager.create_ssh_connection(
            ptp_config.get_gnss_server_host(),
            ptp_config.get_gnss_server_username(),
            ptp_config.get_gnss_server_password(),
        )

        return connection
