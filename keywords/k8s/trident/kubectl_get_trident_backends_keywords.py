"""Keywords for kubectl get tridentbackends operations."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.trident.object.trident_backend_output import TridentBackendOutput


class KubectlGetTridentBackendsKeywords:
    """Keywords for querying Trident storage backends via kubectl.

    Queries tridentbackends resources in the trident namespace to
    discover dataLIF and SVM configuration.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize with SSH connection.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
        """
        self._ssh_connection = ssh_connection

    def get_trident_backends(self) -> TridentBackendOutput:
        """Get all trident backends with dataLIF and SVM info.

        Runs kubectl get tridentbackends with jsonpath to extract
        dataLIF and SVM from each backend configuration. Tries the
        ontap_config nested path first (newer trident), then falls
        back to direct config path (older trident).

        Returns:
            TridentBackendOutput: Parsed trident backend collection.
        """
        # Newer trident versions nest under .config.ontap_config
        cmd = (
            "kubectl get tridentbackends -n trident "
            "-o jsonpath='{range .items[*]}"
            "{.config.ontap_config.dataLIF} {.config.ontap_config.svm}{\"\\n\"}{end}'"
        )
        output = self._ssh_connection.send(export_k8s_config(cmd))
        raw = output if isinstance(output, list) else str(output)
        result = TridentBackendOutput(raw)

        if result.has_backends():
            get_logger().log_info(f"Trident backends found via ontap_config path: {len(raw)} chars")
            return result

        # Fallback: older trident versions use direct .config path
        cmd = (
            "kubectl get tridentbackends -n trident "
            "-o jsonpath='{range .items[*]}"
            "{.config.dataLIF} {.config.svm}{\"\\n\"}{end}'"
        )
        output = self._ssh_connection.send(export_k8s_config(cmd))
        raw = output if isinstance(output, list) else str(output)
        get_logger().log_info(f"Trident backends query (fallback path) returned: {len(raw)} chars")
        return TridentBackendOutput(raw)
