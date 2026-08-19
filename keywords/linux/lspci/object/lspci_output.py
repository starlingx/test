"""Output parser for lspci -nn command."""

import re

from keywords.linux.lspci.object.lspci_device_object import LspciDeviceObject


class LspciOutput:
    """Parses lspci -nn output into a list of LspciDeviceObject instances.

    Expected input format (one device per line):
        0000:b4:00.0 Processing accelerators: Intel Corporation Device [8086:57c0]
        0000:3b:00.0 Ethernet controller: Intel Corporation 82599ES [8086:10fb] (rev 01)
    """

    def __init__(self, raw_output):
        """Constructor.

        Args:
            raw_output: Raw CLI output (str or list of str).
        """
        if isinstance(raw_output, list):
            raw_output = "".join(raw_output)
        self.devices: list[LspciDeviceObject] = []
        self._parse(raw_output)

    def _parse(self, raw_output: str) -> None:
        """Parse lspci -nn output lines into device objects.

        Args:
            raw_output (str): Raw lspci output.
        """
        for line in raw_output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            device = self._parse_line(line)
            if device:
                self.devices.append(device)

    def _parse_line(self, line: str) -> LspciDeviceObject:
        """Parse a single lspci -nn output line.

        Args:
            line (str): Single lspci output line.

        Returns:
            LspciDeviceObject: Parsed device, or None if unparseable.
        """
        device = LspciDeviceObject()
        device.set_raw_line(line)

        # Format: <pci_address> <class>: <description> [<vendor_id>:<device_id>]
        parts = line.split(" ", 1)
        if len(parts) < 2:
            return None

        device.set_pci_address(parts[0])

        remainder = parts[1]
        # Split on first colon to get class vs description
        class_split = remainder.split(": ", 1)
        if len(class_split) >= 2:
            device.set_device_class(class_split[0])
            device.set_description(class_split[1])
        else:
            device.set_description(remainder)

        # Extract vendor:device IDs from brackets [xxxx:xxxx]
        id_match = re.search(r'\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]', line)
        if id_match:
            device.set_vendor_id(id_match.group(1))
            device.set_device_id(id_match.group(2))

        return device

    def get_devices(self) -> list[LspciDeviceObject]:
        """Get all parsed PCI devices.

        Returns:
            list[LspciDeviceObject]: All devices from lspci output.
        """
        return self.devices

    def get_devices_by_pattern(self, pattern: str) -> list[LspciDeviceObject]:
        """Get devices whose raw line matches a pattern (case-insensitive).

        Args:
            pattern (str): Substring to match against the raw lspci line.

        Returns:
            list[LspciDeviceObject]: Matching devices.
        """
        pattern_lower = pattern.lower()
        return [d for d in self.devices if pattern_lower in d.get_raw_line().lower()]

    def get_first_pci_address_by_pattern(self, pattern: str) -> str:
        """Get the PCI address of the first device matching a pattern.

        Args:
            pattern (str): Substring to match (case-insensitive).

        Returns:
            str: PCI address, or empty string if no match.
        """
        matches = self.get_devices_by_pattern(pattern)
        if matches:
            return matches[0].get_pci_address()
        return ""

    def is_empty(self) -> bool:
        """Check if no devices were parsed.

        Returns:
            bool: True if no devices found.
        """
        return len(self.devices) == 0
