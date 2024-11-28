from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class IsIPMIToolKeywords(BaseKeyword):
    """
    Class that checks if IPMI Tools are available on the system.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def is_ipmi_tool_available(self) -> bool:
        """
        This function will check if ipmi tool is available on the system.

        Args: none.

        Returns: True if the ipmi tool is available, false otherwise.

        """
        output = self.ssh_connection.send_as_sudo('ipmitool')

        if "No command provided!" in output:
            return True

        # Output is either "ipmitool: command not found" or, if sudo isn't used:
        # "Could not open device at /dev/ipmi0 or /dev/ipmi/0 or /dev/ipmidev/0: No such file or directory"
        return False
