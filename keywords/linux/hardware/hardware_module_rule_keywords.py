from typing import Tuple

from keywords.base_keyword import BaseKeyword


class HardwareModuleRule(BaseKeyword):
    """
    Mapping between a hardware type (identified by PCI patterns)
    and the kernel modules that should be loaded for that hardware.
    """

    def __init__(self, name: str, pci_patterns: Tuple[str, ...], modules: Tuple[str, ...], resource_name: str):
        """Initializes a HardwareModuleRule.

        Args:
            name: Name for this hardware rule.
            pci_patterns: PCI ID patterns used to identify the hardware.
            modules: Kernel modules that should be loaded for the matched hardware.
            resource_name: Name of the associated resource.
        """
        self._name = name
        self._pci_patterns = pci_patterns
        self._modules = modules
        self._resource_name = resource_name

    def get_name(self) -> str:
        """Returns the name of this hardware rule."""
        return self._name

    def get_pci_patterns(self) -> Tuple[str, ...]:
        """Returns the PCI ID patterns used to identify the hardware."""
        return self._pci_patterns

    def get_modules(self) -> Tuple[str, ...]:
        """Returns the kernel modules for this hardware."""
        return self._modules

    def get_resource_name(self) -> str:
        """Returns the associated resource name."""
        return self._resource_name
