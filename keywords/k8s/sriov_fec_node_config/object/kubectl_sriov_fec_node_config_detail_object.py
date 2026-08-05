from typing import List, Optional

from keywords.k8s.sriov_fec_node_config.object.sriov_fec_accelerator_object import SriovFecAcceleratorObject
from keywords.k8s.sriov_fec_node_config.object.sriov_fec_physical_function_object import SriovFecPhysicalFunctionObject


class KubectlSriovFecNodeConfigDetailObject:
    """Represents the detailed view of a single SriovFecNodeConfig from '-o json' output."""

    def __init__(self, name: Optional[str] = None) -> None:
        """Constructor.

        Args:
            name (Optional[str]): Name of the SriovFecNodeConfig (typically the node name).
        """
        self.name = name
        self.namespace: Optional[str] = None
        self.physical_functions: List[SriovFecPhysicalFunctionObject] = []
        self.accelerators: List[SriovFecAcceleratorObject] = []
        self.configured_reason: Optional[str] = None
        self.configured_status: Optional[str] = None
        self.configured_message: Optional[str] = None

    def get_name(self) -> Optional[str]:
        """Getter for the name.

        Returns:
            Optional[str]: The name of the SriovFecNodeConfig.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Setter for the name.

        Args:
            name (str): The name of the SriovFecNodeConfig.
        """
        self.name = name

    def get_namespace(self) -> Optional[str]:
        """Getter for the namespace.

        Returns:
            Optional[str]: The namespace of the SriovFecNodeConfig.
        """
        return self.namespace

    def set_namespace(self, namespace: str) -> None:
        """Setter for the namespace.

        Args:
            namespace (str): The namespace of the SriovFecNodeConfig.
        """
        self.namespace = namespace

    def get_physical_functions(self) -> List[SriovFecPhysicalFunctionObject]:
        """Getter for the list of physical functions.

        Returns:
            List[SriovFecPhysicalFunctionObject]: The physical functions defined in the spec.
        """
        return self.physical_functions

    def set_physical_functions(self, physical_functions: List[SriovFecPhysicalFunctionObject]) -> None:
        """Setter for the list of physical functions.

        Args:
            physical_functions (List[SriovFecPhysicalFunctionObject]): The physical functions defined in the spec.
        """
        self.physical_functions = physical_functions

    def get_physical_function_by_pci_address(self, pci_address: str) -> SriovFecPhysicalFunctionObject:
        """Return the physical function with the specified PCI address.

        Args:
            pci_address (str): The PCI address of the physical function to retrieve.

        Returns:
            SriovFecPhysicalFunctionObject: The matching physical function.

        Raises:
            ValueError: If no physical function with the specified PCI address is found.
        """
        for physical_function in self.physical_functions:
            if physical_function.get_pci_address() == pci_address:
                return physical_function
        raise ValueError(f"SriovFec physical function with PCI address '{pci_address}' not found")

    def has_physical_function_by_pci_address(self, pci_address: str) -> bool:
        """Check whether a physical function with the specified PCI address is configured.

        A card present in the status inventory is not necessarily configured in the
        spec, so callers can use this before get_physical_function_by_pci_address().

        Args:
            pci_address (str): The PCI address of the physical function to check.

        Returns:
            bool: True if a matching physical function exists, False otherwise.
        """
        for physical_function in self.physical_functions:
            if physical_function.get_pci_address() == pci_address:
                return True
        return False

    def get_accelerators(self) -> List[SriovFecAcceleratorObject]:
        """Getter for the list of accelerators.

        Returns:
            List[SriovFecAcceleratorObject]: The accelerators from the status inventory.
        """
        return self.accelerators

    def set_accelerators(self, accelerators: List[SriovFecAcceleratorObject]) -> None:
        """Setter for the list of accelerators.

        Args:
            accelerators (List[SriovFecAcceleratorObject]): The accelerators from the status inventory.
        """
        self.accelerators = accelerators

    def get_accelerator_by_pci_address(self, pci_address: str) -> SriovFecAcceleratorObject:
        """Return the accelerator with the specified PCI address.

        Args:
            pci_address (str): The PCI address of the accelerator to retrieve.

        Returns:
            SriovFecAcceleratorObject: The matching accelerator.

        Raises:
            ValueError: If no accelerator with the specified PCI address is found.
        """
        for accelerator in self.accelerators:
            if accelerator.get_pci_address() == pci_address:
                return accelerator
        raise ValueError(f"SriovFec accelerator with PCI address '{pci_address}' not found")

    def get_accelerator_by_device_id(self, device_id: str) -> SriovFecAcceleratorObject:
        """Return the first accelerator with the specified device ID.

        Args:
            device_id (str): The device ID of the accelerator to retrieve.

        Returns:
            SriovFecAcceleratorObject: The matching accelerator.

        Raises:
            ValueError: If no accelerator with the specified device ID is found.
        """
        for accelerator in self.accelerators:
            if accelerator.get_device_id() == device_id:
                return accelerator
        raise ValueError(f"SriovFec accelerator with device ID '{device_id}' not found")

    def get_configured_reason(self) -> Optional[str]:
        """Getter for the 'Configured' condition reason.

        Returns:
            Optional[str]: The reason of the 'Configured' status condition (e.g. 'Succeeded').
        """
        return self.configured_reason

    def set_configured_reason(self, configured_reason: str) -> None:
        """Setter for the 'Configured' condition reason.

        Args:
            configured_reason (str): The reason of the 'Configured' status condition.
        """
        self.configured_reason = configured_reason

    def get_configured_status(self) -> Optional[str]:
        """Getter for the 'Configured' condition status.

        Returns:
            Optional[str]: The status of the 'Configured' status condition (e.g. 'True').
        """
        return self.configured_status

    def set_configured_status(self, configured_status: str) -> None:
        """Setter for the 'Configured' condition status.

        Args:
            configured_status (str): The status of the 'Configured' status condition.
        """
        self.configured_status = configured_status

    def get_configured_message(self) -> Optional[str]:
        """Getter for the 'Configured' condition message.

        Returns:
            Optional[str]: The message of the 'Configured' status condition.
        """
        return self.configured_message

    def set_configured_message(self, configured_message: str) -> None:
        """Setter for the 'Configured' condition message.

        Args:
            configured_message (str): The message of the 'Configured' status condition.
        """
        self.configured_message = configured_message

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: Human-readable representation of the SriovFecNodeConfig detail.
        """
        return f"SriovFecNodeConfigDetail(name={self.name}, namespace={self.namespace}, physical_functions={len(self.physical_functions)}, accelerators={len(self.accelerators)}, configured_reason={self.configured_reason})"
