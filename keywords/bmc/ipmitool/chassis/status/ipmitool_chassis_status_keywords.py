from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.bmc.ipmitool.chassis.status.object.ipmitool_chassis_status_object import IPMIToolChassisStatusObject
from keywords.bmc.ipmitool.chassis.status.object.ipmitool_chassis_status_output import IPMIToolChassisStatusOutput


class IPMIToolChassisStatusKeywords(BaseKeyword):
    """
    Keywords for ipmitool chassis status keywords
    """

    def __init__(self, ssh_connection: SSHConnection, host_name):
        self.ssh_connection = ssh_connection

        lab_config = ConfigurationManager.get_lab_config()
        self.bm_password = lab_config.get_bm_password()

        node = lab_config.get_node(host_name)
        self.bm_ip = node.get_bm_ip()
        self.bm_username = node.get_bm_username()

    def get_ipmi_chassis_status(self) -> IPMIToolChassisStatusObject:
        """
        Gets the ipmi chassis status
        Returns: IPMIToolChassisStatusObject

        """
        output = self.ssh_connection.send(f"ipmitool -I lanplus -H {self.bm_ip} -U {self.bm_username} -P {self.bm_password} chassis status")
        chassis_status_output = IPMIToolChassisStatusOutput(output)

        return chassis_status_output.get_ipmitool_chassis_status_object()
