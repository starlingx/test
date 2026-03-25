from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlFileApplyKeywords(K8sBaseKeyword):
    """
    K8s file apply keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Initializes the class with an SSH connection.

        Args:
            ssh_connection (SSHConnection): An instance of SSHConnection to be used for SSH operations.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def apply_resource_from_yaml(self, yaml_file: str, validate: bool = True):
        """
        Applies a Kubernetes resource using the given YAML file.

        Args:
            yaml_file (str): The path to the YAML file containing the resource definition.
            validate (bool): Enable validation. Defaults to True.
        """
        cmd = f"kubectl apply -f {yaml_file}"

        if not validate:
            cmd += " --validate=false"

        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def kubectl_apply_with_error(self, yaml_file: str) -> str:
        """
        Apply Kubernetes resource and return output message.

        Args:
            yaml_file (str): Path to the YAML file containing the resource definition.

        Returns:
            str: Output message from kubectl apply command.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl apply -f {yaml_file}"))
        return "\n".join(output) if isinstance(output, list) else str(output)
