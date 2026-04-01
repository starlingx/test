from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.cat.object.cat_os_release_output import CatOSReleaseOutput


class CatOSKeywords(BaseKeyword):
    """Cat OS command operations for retrieving OS information."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize cat OS keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for cat operations.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def get_os_release(self) -> CatOSReleaseOutput:
        """Gets the content of /etc/os-release and returns structured output.

        Returns:
            CatOSReleaseOutput: Parsed OS release information
        """
        output = self.ssh_connection.send('cat /etc/os-release')
        self.validate_success_return_code(self.ssh_connection)
        return CatOSReleaseOutput(output)
