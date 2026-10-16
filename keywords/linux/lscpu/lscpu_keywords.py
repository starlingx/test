from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.lscpu.object.lscpu_output import LscpuOutput


class LscpuKeywords(BaseKeyword):
    """Keywords for reading CPU topology via the ``lscpu`` command."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize LscpuKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_lscpu(self) -> LscpuOutput:
        """Run ``lscpu`` once and return its parsed output.

        Returns:
            LscpuOutput: The parsed ``lscpu`` output, queried via getters.
        """
        output = self.ssh_connection.send("lscpu")
        self.validate_success_return_code(self.ssh_connection)
        if isinstance(output, list):
            output = "".join(output)
        return LscpuOutput(output)
