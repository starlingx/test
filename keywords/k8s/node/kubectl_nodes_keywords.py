from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.node.object.kubectl_nodes_json_output import KubectlNodesJSONOutput
from keywords.k8s.node.object.kubectl_nodes_output import KubectlNodesOutput


class KubectlNodesKeywords(BaseKeyword):
    """
    Class for Kubectl "kubectl get nodes"  keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection): SSH Connection object
        """
        self.ssh_connection = ssh_connection

    def get_kubectl_nodes(self) -> KubectlNodesOutput:
        """
        Gets the kubectl get nodes

        Returns:
            KubectlNodesOutput:  KubectlNodesOutput object

        """
        output = self.ssh_connection.send(source_openrc(export_k8s_config("kubectl get nodes")))
        self.validate_success_return_code(self.ssh_connection)
        kubectl_nodes_output = KubectlNodesOutput(output)

        return kubectl_nodes_output

    def get_nodes_allocatable_resources(self) -> KubectlNodesJSONOutput:
        """
        Gets allocatable resources for all nodes using JSON output.

        Returns:
            KubectlNodesJSONOutput: Object that parses and provides structured access to allocatable resources.
        """
        raw_out = self.ssh_connection.send(source_openrc(export_k8s_config("kubectl get nodes -o json")))
        self.validate_success_return_code(self.ssh_connection)

        text = "\n".join(raw_out) if isinstance(raw_out, list) else str(raw_out)
        return KubectlNodesJSONOutput(text)
