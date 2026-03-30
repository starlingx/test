from pytest import fail

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCreateTokenKeywords(K8sBaseKeyword):
    """
    Keywords for creating a token with kubectl
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Initializes the KubectlCreateTokenKeywords class with an SSH connection.

        Args:
            ssh_connection (SSHConnection): An object representing the SSH connection.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

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
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl create token {args}"))
        if output and len(output) == 1:
            output = output[0]
        else:
            fail("Token creation failed.")

        self.validate_success_return_code(self.ssh_connection)
        return output
