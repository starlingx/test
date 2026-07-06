from typing import Optional


class SriovFecPhysicalFunctionObject:
    """Represents a single physical function from a SriovFecNodeConfig spec."""

    def __init__(self, pci_address: Optional[str] = None) -> None:
        """Constructor.

        Args:
            pci_address (Optional[str]): PCI address of the physical function.
        """
        self.pci_address = pci_address
        self.pf_driver: Optional[str] = None
        self.vf_driver: Optional[str] = None
        self.vf_amount: Optional[int] = None

    def get_pci_address(self) -> Optional[str]:
        """Getter for the PCI address.

        Returns:
            Optional[str]: The PCI address of the physical function.
        """
        return self.pci_address

    def set_pci_address(self, pci_address: str) -> None:
        """Setter for the PCI address.

        Args:
            pci_address (str): The PCI address of the physical function.
        """
        self.pci_address = pci_address

    def get_pf_driver(self) -> Optional[str]:
        """Getter for the physical function driver.

        Returns:
            Optional[str]: The driver configured for the physical function.
        """
        return self.pf_driver

    def set_pf_driver(self, pf_driver: str) -> None:
        """Setter for the physical function driver.

        Args:
            pf_driver (str): The driver configured for the physical function.
        """
        self.pf_driver = pf_driver

    def get_vf_driver(self) -> Optional[str]:
        """Getter for the virtual function driver.

        Returns:
            Optional[str]: The driver configured for the virtual functions.
        """
        return self.vf_driver

    def set_vf_driver(self, vf_driver: str) -> None:
        """Setter for the virtual function driver.

        Args:
            vf_driver (str): The driver configured for the virtual functions.
        """
        self.vf_driver = vf_driver

    def get_vf_amount(self) -> Optional[int]:
        """Getter for the virtual function amount.

        Returns:
            Optional[int]: The number of virtual functions configured.
        """
        return self.vf_amount

    def set_vf_amount(self, vf_amount: int) -> None:
        """Setter for the virtual function amount.

        Args:
            vf_amount (int): The number of virtual functions configured.
        """
        self.vf_amount = vf_amount

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: Human-readable representation of the physical function.
        """
        return f"SriovFecPhysicalFunction(pci_address={self.pci_address}, pf_driver={self.pf_driver}, vf_driver={self.vf_driver}, vf_amount={self.vf_amount})"
