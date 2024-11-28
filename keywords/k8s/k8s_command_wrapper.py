"""
This file contains the command wrapper that will set the Environment Variables necessary
to execute kubectl commands.
"""

from config.configuration_manager import ConfigurationManager


def export_k8s_config(cmd: str):
    kubeconfig = ConfigurationManager.get_k8s_config().get_kubeconfig()
    return f"export KUBECONFIG={kubeconfig};{cmd}"
