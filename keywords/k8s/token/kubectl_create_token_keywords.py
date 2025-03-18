from pytest import fail

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlCreateTokenKeywords(BaseKeyword):
    """
    Keywords for creating a token with kubectl
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initializes the KubectlCreateTokenKeywords class with an SSH connection.

        Args:
            ssh_connection (SSHConnection): An object representing the SSH connection.
        """
        self.ssh_connection = ssh_connection

    def create_token(self, namespace: str, user: str) -> list:
        """
        Create a Kubernetes token for a specified user in a given namespace.

        Args:
            namespace (str): The Kubernetes namespace where the token will be created.
            user (str): The name of the Kubernetes service account for which the token will be created.

        Returns:
            list: The output from the kubectl command execution.
        """
        args = f"{user} -n {namespace}"
        output = self.ssh_connection.send(export_k8s_config(f"kubectl create token {args}"))
        if output and len(output) == 1:
            output = output[0]
        else:
            fail("Token creation failed.")

        self.validate_success_return_code(self.ssh_connection)
        return output
