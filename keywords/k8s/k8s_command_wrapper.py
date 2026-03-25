"""Command wrapper for kubectl commands.

This file contains the command wrapper that will set the Environment Variables necessary
to execute kubectl commands.
"""

from config.configuration_manager import ConfigurationManager


class K8sConfigExporter:
    """Wrapper class for exporting kubectl commands with KUBECONFIG."""

    _default_instance = None

    def __init__(self, kubeconfig_path: str = None):
        """
        Initialize K8sConfigExporter.

        Args:
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        if kubeconfig_path:
            self.kubeconfig = kubeconfig_path
        else:
            self.kubeconfig = ConfigurationManager.get_k8s_config().get_kubeconfig()

    @classmethod
    def get_default_instance(cls) -> "K8sConfigExporter":
        """Get singleton instance with default config.

        Returns:
            K8sConfigExporter: Default instance.
        """
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    def get_kubeconfig_path(self) -> str:
        """Get the configured KUBECONFIG path.

        Returns:
            str: The KUBECONFIG path.
        """
        return self.kubeconfig

    def export(self, cmd: str) -> str:
        """Export KUBECONFIG environment variable and execute kubectl command.

        Args:
            cmd (str): The kubectl command to execute.

        Returns:
            str: The command string with KUBECONFIG export prepended.
        """
        return f"export KUBECONFIG={self.kubeconfig};{cmd}"


def export_k8s_config(cmd: str) -> str:
    """Export KUBECONFIG environment variable and execute kubectl command.

    Args:
        cmd (str): The kubectl command to execute.

    Returns:
        str: The command string with KUBECONFIG export prepended.
    """
    return K8sConfigExporter.get_default_instance().export(cmd)
