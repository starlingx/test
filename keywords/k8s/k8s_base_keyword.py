"""Base class for kubectl keywords with multi-cluster kubeconfig support."""

from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter


class K8sBaseKeyword(BaseKeyword):
    """Base class for all kubectl keywords with multi-cluster support.

    Provides automatic kubeconfig management for kubectl operations across
    multiple Kubernetes clusters with different kubeconfig locations.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: Optional[str] = None, use_openrc: bool = True) -> None:
        """Initialize kubectl keyword with optional custom kubeconfig.

        Args:
            ssh_connection (SSHConnection): SSH connection to target system.
            kubeconfig_path (Optional[str]): Custom KUBECONFIG path. If None, uses default
                from ConfigurationManager (/etc/kubernetes/admin.conf).
            use_openrc (bool): Whether to source platform openrc before kubectl commands.
                Defaults to True. Set to False for clusters (e.g. MicroK8s) where
                /etc/platform/openrc does not exist and KUBECONFIG alone is sufficient.
                This is a one-per-environment setting shared by all commands in the keyword.
        """
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)
        self.use_openrc = use_openrc

    def source_and_export(self, cmd: str) -> str:
        """Wrap a kubectl command with KUBECONFIG export and, optionally, openrc.

        Always exports KUBECONFIG via the k8s config. When use_openrc is True
        (the default) the command is additionally wrapped with source_openrc;
        when False it is not.

        Args:
            cmd (str): The kubectl command to execute.

        Returns:
            str: The command string ready to send over SSH.
        """
        exported = self.k8s_config.export(cmd)
        return source_openrc(exported) if self.use_openrc else exported
