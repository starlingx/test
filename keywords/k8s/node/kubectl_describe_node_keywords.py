from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.node.object.kubectl_node_description_output import KubectlNodeDescriptionOutput


class KubectlDescribeNodeKeywords(BaseKeyword):
    """
    Class for Kubectl "kubectl describe node" keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def describe_node(self, node_name: str) -> KubectlNodeDescriptionOutput:
        """
        This function will run 'kubectl describe node <node_name>'
        Args:
            node_name: The name of the node to describe

        Returns: A KubectlNodeDescriptionObject representing the description of the Node.

        """
        kubectl_describe_node_output = self.ssh_connection.send(export_k8s_config(f"kubectl describe node {node_name}"))
        self.validate_success_return_code(self.ssh_connection)

        kubectl_node_description_output = KubectlNodeDescriptionOutput(kubectl_describe_node_output)
        return kubectl_node_description_output
