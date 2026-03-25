from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.daemonsets.objects.kubectl_get_daemonsets_output import KubectlGetDaemonsetsOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetDaemonsetsKeywords(K8sBaseKeyword):
    """
    Kubectl get daemonsets keywords class
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        super().__init__(ssh_connection, kubeconfig_path)

    def get_daemonsets(self) -> KubectlGetDaemonsetsOutput:
        """Get all daemonsets returned by the kubectl get daemonsets command.

        Returns:
            KubectlGetDaemonsetsOutput: Parsed daemonsets output.
        """
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get daemonsets"))
        self.validate_success_return_code(self.ssh_connection)
        get_daemonsets_output = KubectlGetDaemonsetsOutput(output)

        return get_daemonsets_output
