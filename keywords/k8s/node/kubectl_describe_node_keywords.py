from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.node.object.kubectl_node_description_output import KubectlNodeDescriptionOutput


class KubectlDescribeNodeKeywords(K8sBaseKeyword):
    """
    Class for Kubectl "kubectl describe node" keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def describe_node(self, node_name: str) -> KubectlNodeDescriptionOutput:
        """Run 'kubectl describe node <node_name>'.

        Args:
            node_name (str): The name of the node to describe.

        Returns:
            KubectlNodeDescriptionOutput: The description of the node.
        """
        kubectl_describe_node_output = self.ssh_connection.send(self.k8s_config.export(f"kubectl describe node {node_name}"))
        self.validate_success_return_code(self.ssh_connection)

        kubectl_node_description_output = KubectlNodeDescriptionOutput(kubectl_describe_node_output)
        return kubectl_node_description_output
