from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.crd.object.kubectl_hosts_output import KubectlHostsOutput
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlHostsKeywords(BaseKeyword):
    """
    Kubectl get keywords for CRDs resources
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

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
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_hosts_output = KubectlHostsOutput(output)

        return get_hosts_output
