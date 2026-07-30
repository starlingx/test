"""Keywords for kubectl get net-attach-def operations."""

from typing import List

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetNetworkAttachmentKeywords(K8sBaseKeyword):
    """Keywords for managing Kubernetes Network Attachment Definitions."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize with SSH connection.

        Args:
            ssh_connection: Active SSH connection.
            kubeconfig_path: Optional kubeconfig path override.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_network_attachment_names(self, namespace: str) -> List[str]:
        """Get list of NetworkAttachmentDefinition names in a namespace.

        Args:
            namespace: The Kubernetes namespace to query.

        Returns:
            List[str]: Names of existing NADs in the namespace.
        """
        output = self.ssh_connection.send(
            self.k8s_config.export(
                f"kubectl get net-attach-def -n {namespace} --no-headers"
                " -o custom-columns=NAME:.metadata.name 2>/dev/null"
            )
        )
        if isinstance(output, list):
            return [line.strip() for line in output if line.strip() and "No resources" not in line]
        return [line.strip() for line in str(output).split("\n") if line.strip() and "No resources" not in line]
