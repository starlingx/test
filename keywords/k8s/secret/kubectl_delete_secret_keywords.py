from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteSecretsKeywords(K8sBaseKeyword):
    """
    Keywords for delete secrets
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_secret(self, secret_name: str, namespace: str) -> str:
        """
        Deletes the specified Kubernetes secret in the given namespace.

        Args:
            secret_name (str): The name of the secret to delete.
            namespace (str): The namespace where the secret is located.

        Returns:
            str: The output from the kubectl delete command.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl delete -n {namespace} secret {secret_name}"))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def cleanup_secret(self, secret_name: str, namespace: str) -> str:
        """
        This method is intended for use in cleanup operations as it doesn't automatically fail the test.

        Args:
            secret_name (str): The name of the secret to delete.
            namespace (str): The namespace where the secret is located.

        Returns:
            str: The output of the delete operation.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl delete -n {namespace} secret {secret_name}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Secret {secret_name} failed to delete")
        return rc
