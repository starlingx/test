from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteSecretsKeywords(BaseKeyword):
    """
    Keywords for delete secrets
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def delete_secret(self, secret_name: str, namespace: str) -> str:
        """
        Deletes the secret
        Args:
            secret_name (): the secret

        Returns: the output

        """
        output = self.ssh_connection.send(export_k8s_config(f"kubectl delete -n {namespace} secret {secret_name}"))
        self.validate_success_return_code(self.ssh_connection)

        return output
