from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlLabelNodeKeywords(K8sBaseKeyword):
    """Class for kubectl label node keywords."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def label_node(self, node_name: str, label_key: str, label_value: str) -> None:
        """Label a Kubernetes node.

        Args:
            node_name (str): Name of the node to label.
            label_key (str): Label key.
            label_value (str): Label value.
        """
        get_logger().log_info(f"Labeling node {node_name} with {label_key}={label_value}")
        self.ssh_connection.send(self.k8s_config.export(f"kubectl label node {node_name} {label_key}={label_value} --overwrite"))
        self.validate_success_return_code(self.ssh_connection)

    def remove_label(self, node_name: str, label_key: str) -> None:
        """Remove a label from a Kubernetes node.

        Args:
            node_name (str): Name of the node.
            label_key (str): Label key to remove.
        """
        get_logger().log_info(f"Removing label {label_key} from node {node_name}")
        self.ssh_connection.send(self.k8s_config.export(f"kubectl label node {node_name} {label_key}-"))
        self.validate_success_return_code(self.ssh_connection)

    def get_node_names_by_label(self, label_key: str, label_value: str) -> list[str]:
        """
        Get node names that have a specific label.

        Example usage::

            # Get all nodes with cpumanager=true
            nodes = label_keywords.get_node_names_by_label("cpumanager", "true")
            # Returns: ["compute-0", "compute-1"]

            # No matching nodes
            nodes = label_keywords.get_node_names_by_label("foo", "bar")
            # Returns: []

        Args:
            label_key (str): Label key to filter by.
            label_value (str): Label value to filter by.

        Returns:
            list[str]: List of node names matching the label.
        """
        # kubectl get nodes -l cpumanager=true -o jsonpath='{.items[*].metadata.name}'
        # Output: "compute-0 compute-1" → split into ["compute-0", "compute-1"]
        cmd = f"kubectl get nodes -l {label_key}={label_value} -o jsonpath='{{.items[*].metadata.name}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        names_str = output[0].strip() if isinstance(output, list) and output else str(output).strip()
        if not names_str:
            return []
        return names_str.split()
