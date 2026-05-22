from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.occtop.object.occtop_output import OcctopOutput


class OcctopKeywords(BaseKeyword):
    """Occtop command operations for retrieving CPU occupancy information."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize occtop keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for occtop operations.
        """
        super().__init__()
        self.ssh_connection = ssh_connection

    def run_occtop(self, period: int = 1) -> OcctopOutput:
        """Execute occtop on the target host and return structured output.

        Args:
            period (int): Number of seconds to run occtop. Must be between 1 and 60. Defaults to 1.

        Returns:
            OcctopOutput: Parsed occtop output.

        Raises:
            ValueError: If period is less than 1 or greater than 60.
        """
        if period < 1 or period > 60:
            raise ValueError(f"Period must be between 1 and 60 seconds, got {period}")

        output = self.ssh_connection.send(f"occtop --period={period}")
        self.validate_success_return_code(self.ssh_connection)
        return OcctopOutput(output)
