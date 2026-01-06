from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.helm.object.kubectl_get_helm_output import KubectlGetHelmOutput
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlGetHelmKeywords(BaseKeyword):
    """Keywords for 'kubectl get helmcharts' operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize KubectlGetHelmKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_helmcharts(self) -> KubectlGetHelmOutput:
        """Get helmcharts using kubectl with custom columns.

        Returns:
            KubectlGetHelmOutput: Parsed helmcharts output.
        """
        cmd = "kubectl get helmcharts.source.toolkit.fluxcd.io -A -o custom-columns=NAME:.metadata.name,CHART:.spec.chart,VERSION:.spec.version"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetHelmOutput(output)
