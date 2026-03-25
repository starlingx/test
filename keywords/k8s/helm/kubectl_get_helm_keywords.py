from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.helm.object.kubectl_get_helm_output import KubectlGetHelmOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetHelmKeywords(K8sBaseKeyword):
    """Keywords for 'kubectl get helmcharts' operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize KubectlGetHelmKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_helmcharts(self) -> KubectlGetHelmOutput:
        """Get helmcharts using kubectl with custom columns.

        Returns:
            KubectlGetHelmOutput: Parsed helmcharts output.
        """
        cmd = "kubectl get helmcharts.source.toolkit.fluxcd.io -A -o custom-columns=NAME:.metadata.name,CHART:.spec.chart,VERSION:.spec.version"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetHelmOutput(output)

    def get_helmchart_by_name(self, name: str, namespace: str) -> KubectlGetHelmOutput:
        """Get specific helmchart by name and namespace.

        Args:
            name (str): The helmchart name.
            namespace (str): The namespace.

        Returns:
            KubectlGetHelmOutput: Parsed helmcharts output.
        """
        cmd = f"kubectl get helmcharts.source.toolkit.fluxcd.io {name} -n {namespace} -o custom-columns=NAME:.metadata.name,CHART:.spec.chart,VERSION:.spec.version"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            return None
        return KubectlGetHelmOutput(output)
