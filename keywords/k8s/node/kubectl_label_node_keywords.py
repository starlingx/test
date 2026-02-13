from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlLabelNodeKeywords(BaseKeyword):
    """Class for kubectl label node keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
        """
        self.ssh_connection = ssh_connection

    def label_node(self, node_name: str, label_key: str, label_value: str) -> None:
        """Label a Kubernetes node.

        Args:
            node_name (str): Name of the node to label.
            label_key (str): Label key.
            label_value (str): Label value.
        """
        get_logger().log_info(f"Labeling node {node_name} with {label_key}={label_value}")
        self.ssh_connection.send(export_k8s_config(f"kubectl label node {node_name} {label_key}={label_value} --overwrite"))
        self.validate_success_return_code(self.ssh_connection)

    def remove_label(self, node_name: str, label_key: str) -> None:
        """Remove a label from a Kubernetes node.

        Args:
            node_name (str): Name of the node.
            label_key (str): Label key to remove.
        """
        get_logger().log_info(f"Removing label {label_key} from node {node_name}")
        self.ssh_connection.send(export_k8s_config(f"kubectl label node {node_name} {label_key}-"))
        self.validate_success_return_code(self.ssh_connection)
