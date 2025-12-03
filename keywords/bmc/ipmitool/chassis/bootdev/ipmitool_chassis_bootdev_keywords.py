import ipaddress

from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class IPMIToolChassisBootdevKeywords(BaseKeyword):
    """
    Class for IPMI Tool Chassis Boot Device Keywords.
    
    Provides methods to configure chassis boot device settings using IPMI commands.
    Supports setting boot device to PXE, disk, CD/DVD, and other boot options.
    """

    def __init__(self, ssh_connection: SSHConnection, host_name: str):
        """Initialize IPMIToolChassisBootdevKeywords with SSH connection and host details.
        
        Args:
            ssh_connection (SSHConnection): SSH connection to the system.
            host_name (str): Name of the host node to configure.
            
        Raises:
            ValueError: If BMC IP is not configured or has invalid format.
        """
        self.ssh_connection = ssh_connection

        lab_config = ConfigurationManager.get_lab_config()
        self.bm_password = lab_config.get_bm_password()
        if host_name:
            node = lab_config.get_node(host_name)
            self.bm_ip = node.get_bm_ip()
            self.bm_username = node.get_bm_username()

            if not self.bm_ip or self.bm_ip == "None":
                raise ValueError("BMC IP address is not configured or is None")
            try:
                ipaddress.ip_address(self.bm_ip)
            except ValueError:
                raise ValueError(f"Invalid BMC IP address format: {self.bm_ip}")

    def set_chassis_bootdev_pxe(self) -> bool:
        """Set chassis boot device to PXE (network boot).
        
        Configures the chassis to boot from the network using PXE protocol.
        This is typically used for OS installation or recovery scenarios.

        Returns:
            bool: True if boot device was successfully set to PXE.
            
        Raises:
            Exception: If command execution fails or returns error.
        """
        cmd_out = self.ssh_connection.send(f"ipmitool -I lanplus -H {self.bm_ip} -U {self.bm_username} -P {self.bm_password} chassis bootdev pxe")
        self.validate_success_return_code(self.ssh_connection)
        return True
