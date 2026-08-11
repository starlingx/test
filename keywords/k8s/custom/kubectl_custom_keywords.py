"""Keywords for managing Kubernetes custom resource instances.

Provides apply and presence-check operations for arbitrary custom resources
such as ServiceMonitor, PodMonitor, PrometheusRule, etc.
"""

from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword

TEMP_CR_FILE_PATH = "/tmp/ace_custom_resource.yaml"


class KubectlCustomKeywords(K8sBaseKeyword):
    """Keywords for managing Kubernetes custom resource instances.

    Supports apply (from inline YAML) and presence-check operations
    on any custom resource type.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: Optional[str] = None) -> None:
        """Initialize keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
            kubeconfig_path (Optional[str]): Custom KUBECONFIG path. If None, uses default.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def apply_custom_resource(self, yaml_content: str, namespace: Optional[str] = None) -> None:
        """Apply a custom resource from YAML content.

        Writes the YAML to a temp file on the remote system, applies it
        via kubectl, and deletes the temp file.

        Args:
            yaml_content (str): YAML content defining the custom resource.
            namespace (Optional[str]): Namespace to apply in. If None, uses
                the namespace from the YAML metadata.

        Raises:
            AssertionError: If kubectl apply fails.
        """
        file_keywords = FileKeywords(self.ssh_connection)
        file_keywords.create_file_with_heredoc(TEMP_CR_FILE_PATH, yaml_content)

        cmd = f"kubectl apply -f {TEMP_CR_FILE_PATH}"
        if namespace:
            cmd += f" -n {namespace}"

        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        file_keywords.delete_file(TEMP_CR_FILE_PATH)
        get_logger().log_info("Applied custom resource from YAML")

    def is_custom_resource_present(
        self,
        resource_type: str,
        resource_name: str,
        namespace: Optional[str] = None,
    ) -> bool:
        """Check if a custom resource exists.

        Args:
            resource_type (str): Resource type (e.g., 'servicemonitor').
            resource_name (str): Resource name.
            namespace (Optional[str]): Namespace to check. If None, uses the
                kubeconfig context's default namespace, so resources in other
                namespaces will not be found.

        Returns:
            bool: True if the resource exists, False otherwise.
        """
        cmd = f"kubectl get {resource_type} {resource_name} -o name"
        if namespace:
            cmd += f" -n {namespace}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        return self.ssh_connection.get_return_code() == 0
