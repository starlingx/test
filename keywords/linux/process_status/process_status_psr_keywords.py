from typing import Optional

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
            pid (int): The process ID.

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

    def get_pid_by_process_name(self, process_name: str) -> Optional[int]:
        """Get the first PID matching a process name.

        Uses ``ps --noheadings -o pid -C <process_name>`` which matches
        the process command name (argv[0]) rather than the full command
        line, making it immune to argument variation.

        Args:
            process_name (str): Process name to search for (matched by ps ``-C`` flag),
                e.g. ``'cyclictest'``.

        Returns:
            Optional[int]: The first matching PID as an integer, or ``None`` if no
                matching process is found.
        """
        output = "".join(self.ssh_connection.send(f"ps --noheadings -o pid -C {process_name}"))
        first_token = output.strip().split()[0] if output.strip() else ""
        if first_token.isdigit():
            return int(first_token)
        return None
