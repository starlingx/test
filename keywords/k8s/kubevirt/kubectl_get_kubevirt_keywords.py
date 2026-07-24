"""Keywords for querying KubeVirt cluster-level information."""

from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.kubevirt.object.kubectl_get_kubevirt_version_output import KubectlGetKubevirtVersionOutput


class KubectlGetKubevirtKeywords(K8sBaseKeyword):
    """Keywords for kubectl get kubevirt operations.

    Queries the KubeVirt custom resource for cluster-level information.
    """

    NOT_INSTALLED = "Not Installed"

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize KubectlGetKubevirtKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_kubevirt_version(self) -> KubectlGetKubevirtVersionOutput:
        """Query the KubeVirt CR and return parsed version output.

        Runs ``kubectl get kubevirt -A -o json`` and parses the JSON into a
        KubectlGetKubevirtVersionOutput. If KubeVirt is not installed the
        command returns an empty items list which the parser handles by setting
        installed=False.

        Returns:
            KubectlGetKubevirtVersionOutput: Parsed output.
        """
        get_logger().log_info("Querying KubeVirt version from cluster")
        cmd = "kubectl get kubevirt -A -o json"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        raw_json = "".join(output) if output else ""
        return KubectlGetKubevirtVersionOutput(raw_json)

    def get_observed_version(self) -> Optional[str]:
        """Convenience: get observed KubeVirt version as a string.

        Returns:
            Optional[str]: Version string (e.g. 'v1.7.0') or None if not installed.
        """
        version_obj = self.get_kubevirt_version().get_kubevirt_version()
        if version_obj.is_installed() and version_obj.get_observed_version():
            get_logger().log_info(f"KubeVirt observed version: {version_obj.get_observed_version()}")
            return version_obj.get_observed_version()
        get_logger().log_info("KubeVirt is not installed on this system")
        return None
