"""Keywords for the 'kubectl get installation' command."""

from framework.logging.automation_logger import get_logger
from keywords.k8s.calico.object.installation_output import InstallationOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetInstallationKeywords(K8sBaseKeyword):
    """Class for the 'kubectl get installation' keyword.

    The Installation CR (operator.tigera.io/v1) holds the configuration the Calico
    operator applies to the cluster.
    """

    def get_installation(self) -> InstallationOutput:
        """Get the default Installation CR as a parsed output object.

        Returns:
            InstallationOutput: An object containing the parsed Installation CR.
        """
        get_logger().log_debug("Getting the default Installation CR")
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get installation default -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return InstallationOutput(output)
