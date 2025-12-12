from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class CatKernelCorePatternKeywords(BaseKeyword):
    """
    Class for '/proc/sys/kernel/core_pattern' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def get_core_pattern(self) -> str:
        """
        Gets the content of the file '/proc/sys/kernel/core_pattern' using 'cat' as sudo.

        Returns: (str) Content of /proc/sys/kernel/core_pattern file

        """
        core_pattern = self.ssh_connection.send_as_sudo("cat /proc/sys/kernel/core_pattern")
        self.validate_success_return_code(self.ssh_connection)

        return core_pattern[0]
