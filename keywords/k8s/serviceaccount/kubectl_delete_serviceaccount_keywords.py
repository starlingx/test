from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteServiceAccountKeywords(BaseKeyword):
    """
    Delete ServiceAccount keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor for KubectlDeleteServiceAccountKeywords.

        Args:
            ssh_connection (SSHConnection): An SSH connection object used to execute commands on the Kubernetes cluster.
        """
        self.ssh_connection = ssh_connection

    def delete_serviceaccount(self, serviceaccount_name: str, nspace: str = None) -> str:
        """
        Deletes the specified Kubernetes service account.

        Args:
            serviceaccount_name (str): The name of the service account to delete.
            nspace (str, optional): The namespace of the service account. Defaults to None.

        Returns:
            str: The output of the kubectl delete command.
        """
        args = ""
        if nspace:
            args += f" -n {nspace} "
        args += f"{serviceaccount_name}"
        output = self.ssh_connection.send(export_k8s_config(f"kubectl delete serviceaccount {args}"))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def cleanup_serviceaccount(self, serviceaccount_name: str, nspace: str = None) -> str:
        """
        Deletes a Kubernetes ServiceAccount,method is used for cleanup purposes.

        Args:
            serviceaccount_name (str): The name of the ServiceAccount to delete.
            nspace (str, optional): The namespace of the ServiceAccount. Defaults to None.

        Returns:
            str: The output of the command.
        """
        args = ""
        if nspace:
            args += f" -n {nspace} "
        args += f"{serviceaccount_name}"
        self.ssh_connection.send(export_k8s_config(f"kubectl delete serviceaccount {args}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"ServiceAccount {serviceaccount_name} failed to delete")
        return rc
