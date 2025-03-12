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

    def create_token(self, nspace: str, user: str) -> str:
        """
        Creates a Kubernetes token for a specified user in a given namespace.

        Args:
            nspace (str): The Kubernetes namespace where the token will be created.
            user (str): The user for whom the token will be created.

        Returns:
                str: The output from the command execution.

        """
        args = f"{user} -n {nspace}"
        output = self.ssh_connection.send(export_k8s_config(f"kubectl create token {args}"))
        self.validate_success_return_code(self.ssh_connection)
        return output
