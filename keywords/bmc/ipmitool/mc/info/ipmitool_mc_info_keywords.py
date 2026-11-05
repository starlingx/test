from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.bmc.ipmitool.mc.info.object.ipmitool_mc_info_object import IPMIToolMcInfoObject
from keywords.bmc.ipmitool.mc.info.object.ipmitool_mc_info_output import IPMIToolMcInfoOutput


class IPMIToolMcInfoKeywords(BaseKeyword):
    """Keywords for ``ipmitool mc info`` run in-band on the host."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Connection to the host whose BMC is queried.
        """
        self.ssh_connection = ssh_connection

    def get_ipmitool_mc_info(self) -> IPMIToolMcInfoObject:
        """Get the identity and firmware of the host's BMC.

        The command goes through the host's local IPMI device, so no BMC
        address or credentials are needed. Check
        ``IsIPMIToolKeywords.is_ipmi_tool_available()`` first.

        Returns:
            IPMIToolMcInfoObject: BMC identity and firmware.
        """
        output = self.ssh_connection.send_as_sudo("ipmitool mc info")
        self.validate_success_return_code(self.ssh_connection)
        return IPMIToolMcInfoOutput(output).get_ipmitool_mc_info_object()
