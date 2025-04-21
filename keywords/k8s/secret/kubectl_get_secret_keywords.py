from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.secret.object.kubectl_get_secret_output import KubectlGetSecretOutput


class KubectlGetSecretsKeywords(BaseKeyword):
    """
    Keyword class for retrieving Kubernetes secrets.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): The SSH connection object.
        """
        self.ssh_connection = ssh_connection

    def get_secrets(self, namespace: str = "default") -> KubectlGetSecretOutput:
        """
        Runs `kubectl get secrets` and returns a parsed output object.

        Args:
            namespace (str): Kubernetes namespace

        Returns:
            KubectlGetSecretOutput: Parsed secrets list
        """
        cmd = f"kubectl get secrets -n {namespace}"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return KubectlGetSecretOutput(output)

    def get_secret_names(self, namespace: str = "default") -> list[str]:
        """
        Returns a list of secret names in the given namespace.

        Args:
            namespace (str): Kubernetes namespace

        Returns:
            list[str]: Secret names
        """
        secrets_output = self.get_secrets(namespace)
        return [secret.get_name() for secret in secrets_output.kubectl_secret]
