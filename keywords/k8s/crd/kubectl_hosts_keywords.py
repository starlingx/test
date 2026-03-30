from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.crd.object.kubectl_hosts_output import KubectlHostsOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlHostsKeywords(K8sBaseKeyword):
    """
    Kubectl get keywords for CRDs resources
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        super().__init__(ssh_connection, kubeconfig_path)

    def get_hosts(self, namespace: str = None) -> KubectlHostsOutput:
        """
        Gets all the hosts returned by the kubectl get hosts command

        Args:
            namespace (str, optional): The namespace to query. Defaults to None.

        Returns:
            KubectlHostsOutput: An object containing the parsed output of the command.
        """
        arg_namespace = ""
        if namespace:
            arg_namespace = f"-n {namespace}"

        cmd = f"kubectl get hosts {arg_namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_hosts_output = KubectlHostsOutput(output)

        return get_hosts_output
