from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class IPMIToolChassisPowerKeywords(BaseKeyword):
    """
    Class for IMPITool Chassis Power Keywords
    """

    def __init__(self, ssh_connection: SSHConnection, host_name: str):
        self.ssh_connection = ssh_connection

        lab_config = ConfigurationManager.get_lab_config()
        self.bm_password = lab_config.get_bm_password()

        node = lab_config.get_node(host_name)
        self.bm_ip = node.get_bm_ip()
        self.bm_username = node.get_bm_username()

    def power_on(self):
        """
        Powers on the host
        Returns:

        """
        self.ssh_connection.send(f"ipmitool -I lanplus -H {self.bm_ip} -U {self.bm_username} -P {self.bm_password} chassis power on")

    def power_off(self):
        """
        Powers off the host
        Returns:

        """
        self.ssh_connection.send(f"ipmitool -I lanplus -H {self.bm_ip} -U {self.bm_username} -P {self.bm_password} chassis power off")
