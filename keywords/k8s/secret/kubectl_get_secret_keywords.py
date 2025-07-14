import json

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.secret.object.kubectl_get_secret_output import KubectlGetSecretOutput
from keywords.k8s.secret.object.kubectl_secret_object import KubectlSecretObject


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

    def get_secret_json_output(self, secret_name: str, namespace: str = "default") -> KubectlSecretObject | None:
        """
        Get a secret as a structured object.

        Args:
            secret_name (str): The name of the Kubernetes secret.
            namespace (str): The namespace where the secret resides.

        Returns:
            KubectlSecretObject | None: The parsed secret object, or None if not found.
        """
        command = f"kubectl get secret {secret_name} -n {namespace} -o json"
        output = self.ssh_connection.send(export_k8s_config(command))
        self.validate_success_return_code(self.ssh_connection)
        if isinstance(output, list):
            output = "".join(output)
        json_obj = json.loads(output)
        secret_obj = KubectlSecretObject(secret_name)
        secret_obj.load_json(json_obj)
        return secret_obj

    def get_certificate_issuer(self, secret_name: str, namespace: str = "default") -> str | None:
        """
        Extract the certificate issuer from a TLS secret.

        Args:
            secret_name (str): The name of the TLS secret.
            namespace (str): The namespace containing the secret.

        Returns:
            str | None: The certificate issuer string if found, otherwise None.
        """
        secret_output = self.get_secret_json_output(secret_name, namespace)
        return secret_output.get_certificate_issuer()

    def get_secret_with_custom_output(self, secret_name: str, namespace: str, output_format: str, extra_parameters: str = None, base64: bool = False) -> str:
        """
        Get a Kubernetes secret with a custom output format and optional extra parameters.

        Args:
            secret_name (str): The name of the secret to retrieve.
            namespace (str): The namespace where the secret is located.
            output_format (str): The output format (e.g., jsonpath, yaml, etc.).
            extra_parameters (str, optional): Additional parameters for the output format.

        Returns:
            str: The output from the kubectl get command.
        """
        command = f"kubectl get secret {secret_name} -n {namespace} -o {output_format}"
        if extra_parameters:
            command += f"={extra_parameters}"
        if base64:
            command += f" | base64 --decode"
        output = self.ssh_connection.send(export_k8s_config(command))

        return ''.join(output)