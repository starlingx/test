"""Keywords for patching Kubernetes Module resources."""

import json

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlPatchModuleKeywords(K8sBaseKeyword):
    """Keywords for patching Kubernetes Module resources."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize kubectl patch module keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def patch_module(self, module_name: str, namespace: str, patch_data: dict, patch_type: str = "strategic") -> None:
        """Patch a Kubernetes Module resource with updated configuration.

        This method applies a patch to a KMM (Kernel Module Management) Module resource,
        allowing for in-place updates such as version upgrades or container image changes
        without recreating the resource.

        Args:
            module_name (str): Name of the module to patch.
            namespace (str): Namespace where the module resource exists.
            patch_data (dict): Patch data as dictionary containing fields to update.
                             Example: {"spec": {"moduleLoader": {"container": {"version": "2.0"}}}}
            patch_type (str): Type of patch operation. Options:
                            - "strategic": Strategic merge patch (default)
                            - "merge": JSON merge patch
                            - "json": JSON patch (RFC 6902)

        Raises:
            KeywordException: If the patch operation fails or module doesn't exist.

        Example:
            >>> patch_data = {"spec": {"moduleLoader": {"container": {"version": "2.0"}}}}
            >>> keywords.patch_module("my-module", "default", patch_data, "merge")
        """
        get_logger().log_info(f"Patching module {module_name} in namespace {namespace} with type {patch_type}")
        patch_json = json.dumps(patch_data)
        cmd = f"kubectl patch modules.kmm.sigs.x-k8s.io {module_name} -n {namespace} --type={patch_type} -p '{patch_json}'"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
