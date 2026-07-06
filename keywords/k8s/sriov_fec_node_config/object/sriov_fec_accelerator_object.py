from typing import List, Optional

from keywords.k8s.sriov_fec_node_config.object.sriov_fec_virtual_function_object import SriovFecVirtualFunctionObject


class SriovFecAcceleratorObject:
    """Represents a single accelerator from a SriovFecNodeConfig status inventory."""

    def __init__(self, pci_address: Optional[str] = None) -> None:
        """Constructor.

        Args:
            pci_address (Optional[str]): PCI address of the accelerator.
        """
        self.pci_address = pci_address
        self.device_id: Optional[str] = None
        self.vendor_id: Optional[str] = None
        self.driver: Optional[str] = None
        self.max_virtual_functions: Optional[int] = None
        self.virtual_functions: List[SriovFecVirtualFunctionObject] = []

    def get_pci_address(self) -> Optional[str]:
        """Getter for the PCI address.

        Returns:
            Optional[str]: The PCI address of the accelerator.
        """
        return self.pci_address

    def set_pci_address(self, pci_address: str) -> None:
        """Setter for the PCI address.

        Args:
            pci_address (str): The PCI address of the accelerator.
        """
        self.pci_address = pci_address

    def get_device_id(self) -> Optional[str]:
        """Getter for the device ID.

        Returns:
            Optional[str]: The device ID of the accelerator.
        """
        return self.device_id

    def set_device_id(self, device_id: str) -> None:
        """Setter for the device ID.

        Args:
            device_id (str): The device ID of the accelerator.
        """
        self.device_id = device_id

    def get_vendor_id(self) -> Optional[str]:
        """Getter for the vendor ID.

        Returns:
            Optional[str]: The vendor ID of the accelerator.
        """
        return self.vendor_id

    def set_vendor_id(self, vendor_id: str) -> None:
        """Setter for the vendor ID.

        Args:
            vendor_id (str): The vendor ID of the accelerator.
        """
        self.vendor_id = vendor_id

    def get_driver(self) -> Optional[str]:
        """Getter for the driver.

        Returns:
            Optional[str]: The driver bound to the accelerator physical function.
        """
        return self.driver

    def set_driver(self, driver: str) -> None:
        """Setter for the driver.

        Args:
            driver (str): The driver bound to the accelerator physical function.
        """
        self.driver = driver

    def get_max_virtual_functions(self) -> Optional[int]:
        """Getter for the maximum number of virtual functions.

        Returns:
            Optional[int]: The maximum number of virtual functions supported.
        """
        return self.max_virtual_functions

    def set_max_virtual_functions(self, max_virtual_functions: int) -> None:
        """Setter for the maximum number of virtual functions.

        Args:
            max_virtual_functions (int): The maximum number of virtual functions supported.
        """
        self.max_virtual_functions = max_virtual_functions

    def get_virtual_functions(self) -> List[SriovFecVirtualFunctionObject]:
        """Getter for the list of virtual functions.

        Returns:
            List[SriovFecVirtualFunctionObject]: The virtual functions of this accelerator.
        """
        return self.virtual_functions

    def set_virtual_functions(self, virtual_functions: List[SriovFecVirtualFunctionObject]) -> None:
        """Setter for the list of virtual functions.

        Args:
            virtual_functions (List[SriovFecVirtualFunctionObject]): The virtual functions of this accelerator.
        """
        self.virtual_functions = virtual_functions

    def get_virtual_function_by_pci_address(self, pci_address: str) -> SriovFecVirtualFunctionObject:
        """Return the virtual function with the specified PCI address.

        Args:
            pci_address (str): The PCI address of the virtual function to retrieve.

        Returns:
            SriovFecVirtualFunctionObject: The matching virtual function.

        Raises:
            ValueError: If no virtual function with the specified PCI address is found.
        """
        for virtual_function in self.virtual_functions:
            if virtual_function.get_pci_address() == pci_address:
                return virtual_function
        raise ValueError(f"SriovFec virtual function with PCI address '{pci_address}' not found")

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: Human-readable representation of the accelerator.
        """
        return f"SriovFecAccelerator(pci_address={self.pci_address}, device_id={self.device_id}, vendor_id={self.vendor_id}, driver={self.driver}, max_virtual_functions={self.max_virtual_functions}, virtual_functions={len(self.virtual_functions)})"
