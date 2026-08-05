from typing import Optional


class SriovFecVirtualFunctionObject:
    """Represents a single virtual function from a SriovFecNodeConfig accelerator inventory."""

    def __init__(self, pci_address: Optional[str] = None) -> None:
        """Constructor.

        Args:
            pci_address (Optional[str]): PCI address of the virtual function.
        """
        self.pci_address = pci_address
        self.device_id: Optional[str] = None
        self.driver: Optional[str] = None

    def get_pci_address(self) -> Optional[str]:
        """Getter for the PCI address.

        Returns:
            Optional[str]: The PCI address of the virtual function.
        """
        return self.pci_address

    def set_pci_address(self, pci_address: str) -> None:
        """Setter for the PCI address.

        Args:
            pci_address (str): The PCI address of the virtual function.
        """
        self.pci_address = pci_address

    def get_device_id(self) -> Optional[str]:
        """Getter for the device ID.

        Returns:
            Optional[str]: The device ID of the virtual function.
        """
        return self.device_id

    def set_device_id(self, device_id: str) -> None:
        """Setter for the device ID.

        Args:
            device_id (str): The device ID of the virtual function.
        """
        self.device_id = device_id

    def get_driver(self) -> Optional[str]:
        """Getter for the driver.

        Returns:
            Optional[str]: The driver bound to the virtual function.
        """
        return self.driver

    def set_driver(self, driver: str) -> None:
        """Setter for the driver.

        Args:
            driver (str): The driver bound to the virtual function.
        """
        self.driver = driver

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: Human-readable representation of the virtual function.
        """
        return f"SriovFecVirtualFunction(pci_address={self.pci_address}, device_id={self.device_id}, driver={self.driver})"
