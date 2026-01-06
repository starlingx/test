from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.lsmod.object.lsmod_output import LsmodOutput


class LsmodKeywords(BaseKeyword):
    """Keywords for lsmod command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize lsmod keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_lsmod_raw(self) -> str:
        return self.ssh_connection.send("lsmod")

    def get_lsmod_output(self) -> LsmodOutput:
        raw = self.get_lsmod_raw()
        return LsmodOutput(raw)
