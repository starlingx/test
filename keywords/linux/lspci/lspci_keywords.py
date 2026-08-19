"""Keywords for lspci command operations."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.lspci.object.lspci_output import LspciOutput


class LspciKeywords(BaseKeyword):
    """Keywords for lspci command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize lspci keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_lspci_devices(self) -> LspciOutput:
        """Get all PCI devices via lspci -nn.

        Returns:
            LspciOutput: Parsed lspci output with device objects.
        """
        output = self.ssh_connection.send("lspci -nn")
        self.validate_success_return_code(self.ssh_connection)
        return LspciOutput(output)

    def get_pci_address_by_pattern(self, pattern: str) -> str:
        """Get the PCI address of the first device matching a pattern.

        Args:
            pattern (str): Substring to search for (case-insensitive).

        Returns:
            str: PCI address, or empty string if no match.
        """
        output = self.get_lspci_devices()
        return output.get_first_pci_address_by_pattern(pattern)

    def has_pci_device(self, patterns: tuple[str, ...]) -> bool:
        """Check if any PCI device matching the given ID patterns exists.

        Args:
            patterns (tuple[str, ...]): PCI device ID strings.

        Returns:
            bool: True if a matching device is found, otherwise False.
        """
        pattern_str = "|".join(patterns)
        cmd = f'lspci -nn | grep -E "{pattern_str}" | wc -l'
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

        return count > 0

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: String representation of LspciKeywords.
        """
        return "LspciKeywords"
