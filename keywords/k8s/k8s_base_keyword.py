"""Base class for kubectl keywords with multi-cluster kubeconfig support."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter


class K8sBaseKeyword(BaseKeyword):
    """Base class for all kubectl keywords with multi-cluster support.

    Provides automatic kubeconfig management for kubectl operations across
    multiple Kubernetes clusters with different kubeconfig locations.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize kubectl keyword with optional custom kubeconfig.

        Args:
            ssh_connection (SSHConnection): SSH connection to target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default
                from ConfigurationManager (/etc/kubernetes/admin.conf).
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)
