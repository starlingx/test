import ipaddress
import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword

# Retry configuration for transient IPMI session failures
_IPMI_POWER_CMD_MAX_RETRIES = 3
_IPMI_POWER_CMD_RETRY_DELAY_SECONDS = 10


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

            if not self.bm_ip or self.bm_ip == "None":
                raise ValueError("BMC IP address is not configured or is None")
            try:
                ipaddress.ip_address(self.bm_ip)
            except ValueError:
                raise ValueError(f"Invalid BMC IP address format: {self.bm_ip}")

    def _send_power_command(self, bm_ip: str, bm_username: str, bm_password: str, action: str):
        """Sends an IPMI chassis power command with retry on session failure.

        BMC IPMI sessions can intermittently fail with
        "Unable to establish IPMI v2 / RMCP+ session". This method
        retries the command before giving up.

        Args:
            bm_ip (str): IP address of the BMC
            bm_username (str): Username for BMC
            bm_password (str): Password for BMC
            action (str): Power action (off, on, cycle)
        """
        command = f"ipmitool -I lanplus -H {bm_ip} -U {bm_username} -P {bm_password} chassis power {action}"

        for attempt in range(_IPMI_POWER_CMD_MAX_RETRIES):
            self.ssh_connection.send(command)

            if self.ssh_connection.get_return_code() == 0:
                return

            if attempt < _IPMI_POWER_CMD_MAX_RETRIES - 1:
                get_logger().log_info(
                    f"IPMI chassis power {action} failed (attempt {attempt + 1}/{_IPMI_POWER_CMD_MAX_RETRIES}). "
                    f"Retrying in {_IPMI_POWER_CMD_RETRY_DELAY_SECONDS}s..."
                )
                time.sleep(_IPMI_POWER_CMD_RETRY_DELAY_SECONDS)
            else:
                get_logger().log_info(
                    f"IPMI chassis power {action} failed after {_IPMI_POWER_CMD_MAX_RETRIES} attempts."
                )

        self.validate_success_return_code(self.ssh_connection)

    def _power_off(self, bm_ip: str, bm_username: str, bm_password: str):
        """Powers off the host using IPMI tool

        Args:
            bm_ip (str): IP address of the BMC
            bm_username (str): Username for BMC
            bm_password (str): Password for BMC
        """
        self._send_power_command(bm_ip, bm_username, bm_password, "off")

    def power_on(self):
        """Powers on the host"""
        self._send_power_command(self.bm_ip, self.bm_username, self.bm_password, "on")

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

    def power_cycle(self):
        """Powers off/on the host"""
        self._send_power_command(self.bm_ip, self.bm_username, self.bm_password, "cycle")
