from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class KernelKeywords(BaseKeyword):
    """
    Class for linux kernal related command keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def trigger_kernel_crash(self):
        """
        Makes the system crash, secondary kernel will be loaded, then will produce a vmcore and reboot.
        """
        password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        self.ssh_connection.send(f'echo {password} | sudo -S bash -c "echo c > /proc/sysrq-trigger"')
