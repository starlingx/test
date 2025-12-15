from keywords.base_keyword import BaseKeyword
from typing import Tuple

class HardwareModuleRule(BaseKeyword):
    """
    Mapping between a hardware type (identified by PCI patterns)
    and the kernel modules that should be loaded for that hardware.
    """

    def __init__(self, name: str, pci_patterns: Tuple[str, ...], modules: Tuple[str, ...]):
        self._name = name
        self._pci_patterns = pci_patterns
        self._modules = modules

    def get_name(self) -> str:
        return self._name

    def get_pci_patterns(self) -> Tuple[str, ...]:
        return self._pci_patterns

    def get_modules(self) -> Tuple[str, ...]:
        return self._modules
