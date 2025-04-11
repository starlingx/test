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
        if host_name:
            node = lab_config.get_node(host_name)
            self.bm_ip = node.get_bm_ip()
            self.bm_username = node.get_bm_username()

    def _power_off(self, bm_ip: str, bm_username: str, bm_password: str):
        """Powers off the host using IPMI tool

        Args:
            bm_ip (str): IP address of the BMC
            bm_username (str): Username for BMC
            bm_password (str): Password for BMC
        """
        self.ssh_connection.send(f"ipmitool -I lanplus -H {bm_ip} -U {bm_username} -P {bm_password} chassis power off")

    def power_on(self):
        """Powers on the host"""
        self.ssh_connection.send(f"ipmitool -I lanplus -H {self.bm_ip} -U {self.bm_username} -P {self.bm_password} chassis power on")

    def power_off(self):
        """Powers off the host"""
        self._power_off(self.bm_ip, self.bm_username, self.bm_password)

    def power_off_subcloud(self, subcloud_name: str):
        """Powers off the host

        Args:
            subcloud_name (str): name of the subcloud to be powered off
        """
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        controllers = sc_config.get_controllers()
        bm_password = sc_config.get_bm_password()

        for controller in controllers:
            self._power_off(controller.get_bm_ip(), controller.get_bm_username(), bm_password)
            self.bm_ip = controller.get_bm_ip()
