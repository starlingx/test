from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteNamespaceKeywords(BaseKeyword):
    """
    Class for Delete namespace keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def delete_namespace(self, namespace: str) -> str:
        """
        Deletes the namespace
        Args:
            namespace (): the namespace

        Returns:

        """
        output = self.ssh_connection.send(export_k8s_config(f"kubectl delete namespace {namespace}"))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def cleanup_namespace(self, namespace: str) -> str:
        """
        For use in cleanup as it doesn't automatically fail the test
        Args:
            namespace (): the namespace

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl delete namespace {namespace}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Namespace {namespace} failed to delete")
        return rc
