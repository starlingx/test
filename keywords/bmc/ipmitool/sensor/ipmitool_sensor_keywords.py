from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.bmc.ipmitool.sensor.object.ipmitool_sensor_object import IPMIToolSensorObject
from keywords.bmc.ipmitool.sensor.object.ipmitool_sensor_output import IPMIToolSensorOutput


class IPMIToolSensorKeywords(BaseKeyword):
    """
    Class for `ipmitool sensor` keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_ipmi_tool_sensor_list(self) -> list[IPMIToolSensorObject]:
        """
        Gets the values measured by the BMC sensors using `ipmitool sensor` command as a list of `IPMIToolSensorObject`
        objects.

        Args: none.

        Returns: list of `IPMIToolSensorObject` objects. Each `IPMIToolSensorObject` object contains the values measured
         by a specific BMC sensor, as well as other metadata.

        Note 1: some of the value sensors can be unavailable in the host where the command is executed.
        Note 2: each host can have a different set of sensors.

        """
        output = self.ssh_connection.send(f'echo {self.ssh_connection.password} | sudo -S ipmitool sensor')
        self.validate_success_return_code(self.ssh_connection)
        ipmi_sensor_output = IPMIToolSensorOutput(output)

        return ipmi_sensor_output.get_ipmitool_sensor_list()
