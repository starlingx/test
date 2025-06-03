from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteHelmReleaseKeywords(BaseKeyword):
    """
    Class for 'kubectl delete hr' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def delete_helm_release(self, namespace: str, helm_name: str) -> str:
        """
        Deletes the helm release for a given namespace.

        Args:
            namespace (str): the namespace
            helm_name (str): the helm release name

        Returns:
             str: the output of the command

        """
        output = self.ssh_connection.send(export_k8s_config(f"kubectl delete hr -n {namespace} {helm_name}"))
        self.validate_success_return_code(self.ssh_connection)

        return output
