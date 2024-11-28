from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.daemonsets.objects.kubectl_get_daemonsets_output import KubectlGetDaemonsetsOutput
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlGetDaemonsetsKeywords(BaseKeyword):
    """
    Kubectl get daemonsets keywords class
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_daemonsets(self) -> KubectlGetDaemonsetsOutput:
        """
        Gets all the daemonsets returned by the kubectl get daemonsets command
        Returns:

        """
        output = self.ssh_connection.send(export_k8s_config('kubectl get daemonsets'))
        self.validate_success_return_code(self.ssh_connection)
        get_daemonsets_output = KubectlGetDaemonsetsOutput(output)

        return get_daemonsets_output
