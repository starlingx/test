import json

from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.node.object.kubectl_node_labels_output import KubectlNodeLabelsOutput
from keywords.k8s.node.object.kubectl_nodes_json_output import KubectlNodesJSONOutput
from keywords.k8s.node.object.kubectl_nodes_output import KubectlNodesOutput


class KubectlNodesKeywords(K8sBaseKeyword):
    """
    Class for Kubectl "kubectl get nodes"  keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection): SSH Connection object
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_kubectl_nodes(self) -> KubectlNodesOutput:
        """
        Gets the kubectl get nodes

        Returns:
            KubectlNodesOutput:  KubectlNodesOutput object

        """
        output = self.ssh_connection.send(source_openrc(self.k8s_config.export("kubectl get nodes")))
        self.validate_success_return_code(self.ssh_connection)
        kubectl_nodes_output = KubectlNodesOutput(output)

        return kubectl_nodes_output

    def get_nodes_allocatable_resources(self) -> KubectlNodesJSONOutput:
        """
        Gets allocatable resources for all nodes using JSON output.

        Returns:
            KubectlNodesJSONOutput: Object that parses and provides structured access to allocatable resources.
        """
        raw_out = self.ssh_connection.send(source_openrc(self.k8s_config.export("kubectl get nodes -o json")))
        self.validate_success_return_code(self.ssh_connection)

        text = "\n".join(raw_out) if isinstance(raw_out, list) else str(raw_out)
        return KubectlNodesJSONOutput(text)

    def get_node_labels(self, node_name: str) -> KubectlNodeLabelsOutput:
        """Gets all labels for a specific node.

        Args:
            node_name (str): Name of the node.

        Returns:
            KubectlNodeLabelsOutput: Output object with label data and helper methods.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get node {node_name} -o json"))
        self.validate_success_return_code(self.ssh_connection)
        raw_json = "\n".join(output) if isinstance(output, list) else str(output)
        node_data = json.loads(raw_json)
        labels = node_data.get("metadata", {}).get("labels", {})
        return KubectlNodeLabelsOutput(labels)
