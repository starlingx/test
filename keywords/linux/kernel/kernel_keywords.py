from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class KernelKeywords(BaseKeyword):
    """Class for linux kernel related command keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize KernelKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_kernel_version(self) -> str:
        """Get the running kernel version via uname -r.

        Returns:
            str: The kernel version string (e.g., '6.12.0-1-amd64').
        """
        output = self.ssh_connection.send("uname -r")
        self.validate_success_return_code(self.ssh_connection)
        return output[0].strip()

    def trigger_kernel_crash(self):
        """
        Makes the system crash, secondary kernel will be loaded, then will produce a vmcore and reboot.

        The connection is expected to be lost after this command executes.
        """
        password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        try:
            self.ssh_connection.send(f'echo {password} | sudo -S bash -c "echo c > /proc/sysrq-trigger"', command_timeout=10, reconnect_timeout=10)
        except Exception:
            pass

    def verify_kernel_flag(self, expected_flag: str) -> bool:
        """Verify that the running kernel's ``uname -a`` output contains a specific flag.

        Args:
            expected_flag (str): Token to search for in ``uname -a`` output,
                e.g. ``'PREEMPT_RT'`` for a real-time kernel or
                ``'PREEMPT_DYNAMIC'`` for a standard kernel.

        Returns:
            bool: ``True`` if *expected_flag* appears in the ``uname -a`` output,
                ``False`` otherwise.
        """
        output = "".join(self.ssh_connection.send("uname -a"))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"uname -a: {output.strip()}")
        return expected_flag in output
