from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlFileApplyKeywords(BaseKeyword):
    """
    K8s file apply keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initializes the class with an SSH connection.

        Args:
            ssh_connection (SSHConnection): An instance of SSHConnection to be used for SSH operations.
        """
        self.ssh_connection = ssh_connection

    def apply_resource_from_yaml(self, yaml_file: str):
        """
        Applies a Kubernetes resource using the given YAML file.

        Args:
            yaml_file (str): The path to the YAML file containing the resource definition.
        """
        self.ssh_connection.send(export_k8s_config(f"kubectl apply -f {yaml_file}"))
        self.validate_success_return_code(self.ssh_connection)

    def kubectl_apply_with_error(self, yaml_file: str) -> str:
        """
        Apply Kubernetes resource and return output message.

        Args:
            yaml_file (str): Path to the YAML file containing the resource definition.

        Returns:
            str: Output message from kubectl apply command.
        """
        output = self.ssh_connection.send(export_k8s_config(f"kubectl apply -f {yaml_file}"))
        return "\n".join(output) if isinstance(output, list) else str(output)
