from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_is_digit
from keywords.base_keyword import BaseKeyword


class ProcessStatusPsrKeywords(BaseKeyword):
    """Class for getting PSR (processor) information of a process."""

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_psr_for_pid(self, pid: int) -> int:
        """Get the PSR (processor) assigned to a given PID.

        Args:
            pid: The process ID.

        Returns:
            int: The processor number (PSR) the process is running on.
            Example:
                # Get PSR for process with PID 1234
                "ps -o psr= -p 1234"
                # Returns: 2 (meaning process is running on CPU core 2)
        """
        output = self.ssh_connection.send(f"ps -o psr= -p {pid}")
        self.validate_success_return_code(self.ssh_connection)
        psr_str = output[0].strip() if isinstance(output, list) else str(output).strip()
        validate_is_digit(psr_str, f"Expected numeric PSR, got: {psr_str}")
        return int(psr_str)
