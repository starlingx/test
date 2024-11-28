from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteNetworkDefinitionKeywords(BaseKeyword):
    """
    Class for Kubectl Delete Network definitions
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def delete_network_definition(self, network_def_name):
        """
        Deletes the given network definition
        Args:
            network_def_name (): the name of the network definition

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f'kubectl delete net-attach-def {network_def_name}'))
        self.validate_success_return_code(self.ssh_connection)

    def cleanup_network_definition(self, network_def_name):
        """
        Cleanup - used for cleaning up network definitions. Does not fail on code non zero.
        Args:
            network_def_name (): the network definition name

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f'kubectl delete net-attach-def {network_def_name}'))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Pod {network_def_name} failed to delete")
        return rc
