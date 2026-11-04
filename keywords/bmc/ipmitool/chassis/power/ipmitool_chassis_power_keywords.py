import subprocess
import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.bmc.ipmitool.bmc_credentials import resolve_bmc_credentials

from config.configuration_manager import ConfigurationManager

# Retry configuration for transient IPMI session failures
_IPMI_POWER_CMD_MAX_RETRIES = 3
_IPMI_POWER_CMD_RETRY_DELAY_SECONDS = 10

_IPMI_NOT_SUPPORTED_IN_PRESENT_STATE = "not supported in present state"


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
            # Reuse the shared BMC credential resolver for the node's BMC IP /
            # username and the BMC IP validation, so this logic is not
            # duplicated across IPMI keywords. The password is intentionally
            # left as the lab-level bm_password set above (this keyword's
            # existing behavior); no per-node password fallback is applied here.
            bmc = resolve_bmc_credentials(node)
            self.bm_ip = bmc.get_bm_ip()
            self.bm_username = bmc.get_bm_username()

    def _send_power_command(self, bm_ip: str, bm_username: str, bm_password: str, action: str) -> None:
        """Sends an IPMI chassis power command with retry on session failure.

        BMC IPMI sessions can intermittently fail with
        "Unable to establish IPMI v2 / RMCP+ session". This method
        retries the command before giving up.

        For "power on" and "power off", if the BMC rejects with "Command
        not supported in present state" the desired terminal state is
        already reached (the chassis is already on, or already off), so the
        error is treated as non-fatal. For power on, the caller's
        is_powered_on() poll will wait for the chassis to finish powering
        on by itself.

        Args:
            bm_ip (str): IP address of the BMC
            bm_username (str): Username for BMC
            bm_password (str): Password for BMC
            action (str): Power action (off, on, cycle)

        Returns:
            None:
        """
        command = f"ipmitool -I lanplus -H {bm_ip} -U {bm_username} -P {bm_password} chassis power {action}"

        for attempt in range(_IPMI_POWER_CMD_MAX_RETRIES):
            output = self.ssh_connection.send(command)

            if self.ssh_connection.get_return_code() == 0:
                return

            output_str = output if isinstance(output, str) else "\n".join(output)

            # "Command not supported in present state" means the chassis is
            # already in the requested terminal state. On power-on the BMC is
            # already transitioning up (e.g., Power Restore Policy); on
            # power-off the chassis is already off. Either way the desired
            # state is reached, so treat it as non-fatal. For power-on the
            # caller's is_powered_on() poll will handle the wait.
            if action in ("on", "off") and _IPMI_NOT_SUPPORTED_IN_PRESENT_STATE in output_str.lower():
                get_logger().log_info(f"IPMI chassis power {action} rejected: 'Command not supported in present state'. Chassis is already in the requested state. Treating as non-fatal.")
                return

            if attempt < _IPMI_POWER_CMD_MAX_RETRIES - 1:
                get_logger().log_info(f"IPMI chassis power {action} failed (attempt {attempt + 1}/{_IPMI_POWER_CMD_MAX_RETRIES}). " f"Retrying in {_IPMI_POWER_CMD_RETRY_DELAY_SECONDS}s...")
                time.sleep(_IPMI_POWER_CMD_RETRY_DELAY_SECONDS)
            else:
                get_logger().log_info(f"IPMI chassis power {action} failed after {_IPMI_POWER_CMD_MAX_RETRIES} attempts.")

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
            # Persist the BMC connection details so a subsequent power_on()
            # (which reads self.bm_*) can target the same subcloud controller.
            self.bm_ip = controller.get_bm_ip()
            self.bm_username = controller.get_bm_username()
            self.bm_password = bm_password

    def power_cycle(self):
        """Powers off/on the host"""
        self._send_power_command(self.bm_ip, self.bm_username, self.bm_password, "cycle")

    def power_off_from_localhost(self, host_name: str, ignore_error: bool = False) -> int:
        """Run ``ipmitool chassis power off`` locally against a host's BMC.

        The IPMI command is executed on the machine running the automation
        (localhost) rather than over an SSH connection. This is required for
        power operations on a simplex lab, where the only controller's SSH
        session dies when it is powered off, so a command issued over that
        connection would never reach the BMC. The BMC connection details are
        read from the lab configuration for the given host.

        Args:
            host_name (str): The name of the host whose BMC to target
                (e.g. "controller-0").
            ignore_error (bool): When False (default), a non-zero ipmitool
                return code raises a KeywordException. When True, the
                non-zero return code is logged and returned to the caller
                without raising.

        Returns:
            int: The ipmitool process return code (0 on success).

        Raises:
            KeywordException: If ipmitool returns a non-zero code and
                ``ignore_error`` is False.
        """
        lab_config = ConfigurationManager.get_lab_config()
        node = lab_config.get_node(host_name)
        bmc = resolve_bmc_credentials(node, password_fallback_config=lab_config)
        bm_ip = bmc.get_bm_ip()

        cmd = ["ipmitool", "-I", "lanplus", "-H", bm_ip, "-U", bmc.get_bm_username(), "-P", bmc.get_bm_password(), "chassis", "power", "off"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        get_logger().log_info(f"ipmitool chassis power off for {host_name} ({bm_ip}) " f"rc={result.returncode} out={result.stdout.strip()} err={result.stderr.strip()}")

        if result.returncode != 0 and not ignore_error:
            raise KeywordException(f"ipmitool chassis power off for {host_name} ({bm_ip}) failed with return code {result.returncode}: {result.stderr.strip()}")

        return result.returncode

    def power_on_from_localhost(self, host_name: str, ignore_error: bool = False) -> int:
        """Run ``ipmitool chassis power on`` locally against a host's BMC.

        The IPMI command is executed on the machine running the automation
        (localhost) rather than over an SSH connection. This is required for
        power operations on a simplex lab, where the only controller's SSH
        session dies when it is powered off, so a command issued over that
        connection would never reach the BMC. The BMC connection details are
        read from the lab configuration for the given host.

        Args:
            host_name (str): The name of the host whose BMC to target
                (e.g. "controller-0").
            ignore_error (bool): When False (default), a non-zero ipmitool
                return code raises a KeywordException. When True, the
                non-zero return code is logged and returned to the caller
                without raising.

        Returns:
            int: The ipmitool process return code (0 on success).

        Raises:
            KeywordException: If ipmitool returns a non-zero code and
                ``ignore_error`` is False.
        """
        lab_config = ConfigurationManager.get_lab_config()
        node = lab_config.get_node(host_name)
        bmc = resolve_bmc_credentials(node, password_fallback_config=lab_config)
        bm_ip = bmc.get_bm_ip()

        cmd = ["ipmitool", "-I", "lanplus", "-H", bm_ip, "-U", bmc.get_bm_username(), "-P", bmc.get_bm_password(), "chassis", "power", "on"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        get_logger().log_info(f"ipmitool chassis power on for {host_name} ({bm_ip}) " f"rc={result.returncode} out={result.stdout.strip()} err={result.stderr.strip()}")

        if result.returncode != 0 and not ignore_error:
            raise KeywordException(f"ipmitool chassis power on for {host_name} ({bm_ip}) failed with return code {result.returncode}: {result.stderr.strip()}")

        return result.returncode

    def reset_from_localhost(self, host_name: str, subcloud_name: str = None, ignore_error: bool = False) -> int:
        """Run ``ipmitool chassis power reset`` locally against a host's BMC.

        Companion to :meth:`power_off_from_localhost` / :meth:`power_on_from_localhost`
        for the ``reset`` action (a single power-cycle that reboots the node,
        e.g. back into GRUB). The IPMI command is executed on the machine running
        the automation (localhost) rather than over an SSH connection, which is
        required for power operations on a simplex lab where the only
        controller's SSH session dies when it reboots.

        The BMC connection details are resolved from the lab configuration via
        the shared resolver. When ``subcloud_name`` is given, the host is
        resolved on that subcloud's config (with the subcloud-level bm_password
        fallback); otherwise it is resolved on the top-level lab config.

        Args:
            host_name (str): The name of the host whose BMC to target
                (e.g. "controller-0").
            subcloud_name (str): When set, resolve the host on this subcloud's
                config instead of the top-level lab. Defaults to None.
            ignore_error (bool): When False (default), a non-zero ipmitool
                return code raises a KeywordException. When True, the non-zero
                return code is logged and returned to the caller without raising.

        Returns:
            int: The ipmitool process return code (0 on success).

        Raises:
            KeywordException: If ipmitool returns a non-zero code and
                ``ignore_error`` is False.
        """
        lab_config = ConfigurationManager.get_lab_config()
        if subcloud_name:
            scope_config = lab_config.get_subcloud(subcloud_name)
        else:
            scope_config = lab_config
        node = scope_config.get_node(host_name)
        bmc = resolve_bmc_credentials(node, password_fallback_config=scope_config)
        target = subcloud_name or host_name

        cmd = ["ipmitool", "-I", "lanplus", "-H", bmc.get_bm_ip(), "-U", bmc.get_bm_username(), "-P", bmc.get_bm_password(), "chassis", "power", "reset"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        get_logger().log_info(f"ipmitool chassis power reset for {target}/{host_name} ({bmc.get_bm_ip()}) " f"rc={result.returncode} out={result.stdout.strip()} err={result.stderr.strip()}")

        if result.returncode != 0 and not ignore_error:
            raise KeywordException(f"ipmitool chassis power reset for {target}/{host_name} ({bmc.get_bm_ip()}) failed with return code {result.returncode}: {result.stderr.strip()}")

        return result.returncode
