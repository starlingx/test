"""Object representing a single PCI device from lspci output."""


class LspciDeviceObject:
    """Represents a single PCI device entry from lspci -nn output.

    Fields parsed from format: <address> <class>: <vendor> <device> [<id>]
    Example: 0000:b4:00.0 Processing accelerators: Intel Corporation Device [8086:57c0]
    """

    def __init__(self):
        """Initialize LspciDeviceObject."""
        self.pci_address = None
        self.device_class = None
        self.description = None
        self.vendor_id = None
        self.device_id = None
        self.raw_line = None

    def set_pci_address(self, pci_address: str):
        """Set PCI address.

        Args:
            pci_address (str): PCI address (e.g. '0000:b4:00.0').
        """
        self.pci_address = pci_address

    def get_pci_address(self) -> str:
        """Get PCI address.

        Returns:
            str: PCI address (e.g. '0000:b4:00.0').
        """
        return self.pci_address

    def set_device_class(self, device_class: str):
        """Set device class.

        Args:
            device_class (str): Device class (e.g. 'Processing accelerators').
        """
        self.device_class = device_class

    def get_device_class(self) -> str:
        """Get device class.

        Returns:
            str: Device class.
        """
        return self.device_class

    def set_description(self, description: str):
        """Set device description.

        Args:
            description (str): Full description string.
        """
        self.description = description

    def get_description(self) -> str:
        """Get device description.

        Returns:
            str: Full description string.
        """
        return self.description

    def set_vendor_id(self, vendor_id: str):
        """Set vendor ID.

        Args:
            vendor_id (str): Vendor ID (e.g. '8086').
        """
        self.vendor_id = vendor_id

    def get_vendor_id(self) -> str:
        """Get vendor ID.

        Returns:
            str: Vendor ID.
        """
        return self.vendor_id

    def set_device_id(self, device_id: str):
        """Set device ID.

        Args:
            device_id (str): Device ID (e.g. '57c0').
        """
        self.device_id = device_id

    def get_device_id(self) -> str:
        """Get device ID.

        Returns:
            str: Device ID.
        """
        return self.device_id

    def set_raw_line(self, raw_line: str):
        """Set raw lspci output line.

        Args:
            raw_line (str): Original lspci output line.
        """
        self.raw_line = raw_line

    def get_raw_line(self) -> str:
        """Get raw lspci output line.

        Returns:
            str: Original lspci output line.
        """
        return self.raw_line

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: String representation of LspciDeviceObject.
        """
        return f"LspciDevice(address={self.pci_address}, desc={self.description})"
