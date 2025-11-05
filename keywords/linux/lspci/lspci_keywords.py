from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class LspciKeywords(BaseKeyword):
    """Keywords for lsmod command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize lspci keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def has_pci_device(self, patterns: tuple[str, ...]) -> bool:
        """
        Check if any PCI device matching the given ID patterns exists.

        Args:
            ssh_connection: SSHConnection object with .send(cmd) method
            patterns : PCI device ID strings
        Returns:
            bool: True if a matching device is found, otherwise False
        """

        pattern_str = "|".join(patterns)
        cmd = f'lspci -nn | grep -E "{pattern_str}"| wc -l'
        device_output = self.ssh_connection.send(cmd)

        if isinstance(device_output, list):
            device_output = "".join(device_output)
        elif device_output is None:
            return False

        device_output = device_output.strip()

        try:
            count = int(device_output)
        except ValueError:
            return False
        if count > 0:
            return True
        else:
            return False
