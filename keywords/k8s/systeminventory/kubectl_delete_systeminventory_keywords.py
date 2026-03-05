from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteSystemInventoryKeywords(BaseKeyword):
    """
    Keywords for deleting SystemInventory resources.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object
        """
        self.ssh_connection = ssh_connection

    def delete_system_inventory(self, sysinv_name: str, namespace: str) -> str:
        """
        Deletes the specified SystemInventory resource in the given namespace.

        Args:
            sysinv_name (str): The name of the SystemInventory to delete.
            namespace (str): The namespace where the SystemInventory is located.

        Returns:
            str: The output from the kubectl delete command.
        """
        output = self.ssh_connection.send(export_k8s_config(f"kubectl delete -n {namespace} systeminventory {sysinv_name}"))
        self.validate_success_return_code(self.ssh_connection)
        return output
