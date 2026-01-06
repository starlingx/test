from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.lspci.lspci_keywords import LspciKeywords
from keywords.linux.hardware.hardware_module_rule_keywords import HardwareModuleRule
from typing import Tuple

class HardwareKeywords(BaseKeyword):
    """Keywords for lsmod command operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize lsmod keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self._rules: Tuple[HardwareModuleRule, ...] = (
            HardwareModuleRule(
                name="Intel QAT 401xx",
                pci_patterns=("8086:4942", "8086:4943"),
                modules=("intel_qat", "qat_4xxx", "qat_4xxxvf"),
            ),
            HardwareModuleRule(
                name="Intel QAT 420xx",
                pci_patterns=("8086:4946", "8086:4947"),
                modules=("intel_qat", "qat_420xx", "qat_420xxvf"),
            ),
        )

    def get_required_modules(self) -> Tuple[str, ...]:
        """Return all kernel modules required for detected hardware."""
        modules: set[str] = set()

        lspci_keywords = LspciKeywords(self.ssh_connection)
        for rule in self._rules:
            if lspci_keywords.has_pci_device(rule.get_pci_patterns()):
                modules.update(rule.get_modules())
        return tuple(modules)
