from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class VgdisplayKeywords(BaseKeyword):
    """Keywords for vgdisplay client operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
        """
        self._ssh_connection: SSHConnection = ssh_connection

    def get_cgts_vg_free_space(self) -> float:
        """
        Gets the free space available in the cgts-vg volume group.

        Returns:
            float: The free space in GiB.
        """
        command = "vgdisplay -C --noheadings --nosuffix -o vg_free --units g cgts-vg"
        output = self._ssh_connection.send_as_sudo(command)
        self.validate_success_return_code(self._ssh_connection)
        return float("".join(output).strip().splitlines()[0].strip())
