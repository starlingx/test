from config.configuration_manager import ConfigurationManager
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
        """
        password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        self.ssh_connection.send(f'echo {password} | sudo -S bash -c "echo c > /proc/sysrq-trigger"')
