from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class VirtctlKeywords(BaseKeyword):
    """Keywords for virtctl client operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
        """
        self._ssh_connection: SSHConnection = ssh_connection

    def virtctl_pause(self, vm_name: str) -> str:
        """
        Pause a virtual machine.

        Args:
            vm_name (str): Name of the VM to pause.

        Returns:
            str: Command output.

        Raises:
            Exception: If command execution fails.
        """
        output = self._ssh_connection.send(f"virtctl pause vm {vm_name}", fail_ok=False)
        self.validate_success_return_code(self._ssh_connection)
        return output
