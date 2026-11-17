"""Keywords for patching the Calico Installation CR."""

import json
import shlex

from framework.logging.automation_logger import get_logger
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlPatchInstallationKeywords(K8sBaseKeyword):
    """Class for the 'kubectl patch installation' keyword.

    The Installation CR (operator.tigera.io/v1) holds the configuration the Calico
    operator applies to the cluster.
    """

    def patch_installation_merge(self, patch: dict) -> None:
        """Apply a merge patch to the default Installation CR.

        A field set to None is removed, and removing a field that is not set is a no-op, so
        the same call can safely revert a field in teardown.

        Example:
            patch_installation_merge({"spec": {"calicoNetwork": {"mtu": 2000}}}) sets a custom MTU.
            patch_installation_merge({"spec": {"calicoNetwork": {"mtu": None}}}) removes it.

        Args:
            patch (dict): The merge patch body.
        """
        patch_json = json.dumps(patch)
        get_logger().log_info(f"Merge-patching the Installation CR with: {patch_json}")
        cmd = f"kubectl patch installation default --type merge -p {shlex.quote(patch_json)}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
