from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteNetworkDefinitionKeywords(K8sBaseKeyword):
    """
    Class for Kubectl Delete Network definitions
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_network_definition(self, network_def_name: str) -> None:
        """Delete the given network definition.

        Args:
            network_def_name (str): The name of the network definition.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl delete net-attach-def {network_def_name}"))
        self.validate_success_return_code(self.ssh_connection)

    def cleanup_network_definition(self, network_def_name: str) -> int:
        """Delete a network definition without failing on non-zero return code.

        Args:
            network_def_name (str): The network definition name.

        Returns:
            int: The return code of the delete command.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl delete net-attach-def {network_def_name}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Pod {network_def_name} failed to delete")
        return rc
