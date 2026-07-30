"""Keywords for generic kubectl get operations on any resource type."""

from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetResourceKeywords(K8sBaseKeyword):
    """Keywords for generic kubectl get operations on any resource type."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: Optional[str] = None) -> None:
        """Initialize keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
            kubeconfig_path (Optional[str]): Custom KUBECONFIG path. If None, uses default.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_resource_field(self, resource_type: str, resource_name: str, jsonpath: str, namespace: Optional[str] = None) -> str:
        """Get a field from any Kubernetes resource using jsonpath.

        This is an escape hatch for resource types that do not yet have a
        dedicated Output object. Prefer typed keyword/Output pairs when available.

        Args:
            resource_type (str): Resource type (e.g., 'servicemonitor', 'pod', 'deployment').
            resource_name (str): Resource name.
            jsonpath (str): JSONPath expression (e.g., '{.metadata.name}', '{.spec.retention}').
            namespace (Optional[str]): Namespace. If None, uses default namespace.

        Returns:
            str: The field value.

        Raises:
            AssertionError: If kubectl get fails.
        """
        cmd = f"kubectl get {resource_type} {resource_name} -o jsonpath='{jsonpath}'"
        if namespace:
            cmd += f" -n {namespace}"

        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        output_text = "\n".join(output) if isinstance(output, list) else output
        return output_text.strip()
