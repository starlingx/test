from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteNamespaceKeywords(K8sBaseKeyword):
    """
    Class for Delete namespace keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_namespace(self, namespace: str) -> str:
        """Delete the namespace.

        Args:
            namespace (str): The namespace to delete.

        Returns:
            str: The output of the delete command.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl delete namespace {namespace}"))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def cleanup_namespace(self, namespace: str) -> str:
        """Delete a namespace without failing the test on non-zero return code.

        Args:
            namespace (str): The namespace to delete.

        Returns:
            str: The return code of the delete command.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl delete namespace {namespace}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Namespace {namespace} failed to delete")
        return rc
