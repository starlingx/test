from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.daemonsets.objects.kubectl_get_daemonsets_output import KubectlGetDaemonsetsOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetDaemonsetsKeywords(K8sBaseKeyword):
    """
    Kubectl get daemonsets keywords class
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        super().__init__(ssh_connection, kubeconfig_path)

    def get_daemonsets(self, namespace: str = None) -> KubectlGetDaemonsetsOutput:
        """Get the daemonsets returned by the kubectl get daemonsets command.

        Args:
            namespace (str, optional): namespace to query (-n <namespace>). When None, the command
                runs without a namespace flag, preserving the previous default-namespace behaviour.

        Returns:
            KubectlGetDaemonsetsOutput: Parsed daemonsets output.
        """
        namespace_arg = f" -n {namespace}" if namespace else ""
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get daemonsets{namespace_arg}"))
        self.validate_success_return_code(self.ssh_connection)
        get_daemonsets_output = KubectlGetDaemonsetsOutput(output)

        return get_daemonsets_output
