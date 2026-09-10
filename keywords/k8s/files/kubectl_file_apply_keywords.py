from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
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

    def apply_resource_from_yaml_with_retry(self, yaml_file: str, timeout: int = 60, poll_interval: int = 5) -> None:
        """Apply a Kubernetes resource, retrying on transient failures.

        Useful when an admission webhook (e.g. the KubeVirt virt-api mutator) may
        not be reachable yet right after an app is applied. Retries the apply until
        it returns a zero exit code or the timeout is reached.

        Args:
            yaml_file (str): The path to the YAML file containing the resource definition.
            timeout (int): Maximum time to wait in seconds. Defaults to 60.
            poll_interval (int): Time between retries in seconds. Defaults to 5.

        Raises:
            TimeoutError: If the apply does not succeed within the timeout.
        """
        def _apply_return_code() -> int:
            self.ssh_connection.send(self.k8s_config.export(f"kubectl apply -f {yaml_file}"))
            return self.ssh_connection.get_return_code()

        validate_equals_with_retry(
            function_to_execute=_apply_return_code,
            expected_value=0,
            validation_description=f"kubectl apply -f {yaml_file} to succeed",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

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
