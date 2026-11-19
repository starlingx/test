from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.node.object.kubectl_label_node_list_output import KubectlLabelNodeListOutput


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

    def get_node_labels_list(self, node_name: Optional[str] = None) -> KubectlLabelNodeListOutput:
        """Get the labels of one node, or of every node, as an Output object.

        Runs ``kubectl label node --list <node_name>`` (or ``--list --all`` when no
        node is given) once, with no shell pipe. Filtering and counting by prefix
        are done on the returned Output object.

        Args:
            node_name (Optional[str]): Name of the node to list. If None, lists every node.

        Returns:
            KubectlLabelNodeListOutput: Output object with the labels grouped by node.
        """
        target = node_name if node_name else "--all"
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl label node --list {target}"))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlLabelNodeListOutput(output, node_name)

    def count_labels_all_nodes_by_prefix(self, label_prefix: str) -> int:
        """Count labels across all nodes whose key matches a prefix.

        Lists the labels of every node with a single ``kubectl label node --list --all``
        call and counts the matching keys on the ``KubectlLabelNodeListOutput`` object.

        Args:
            label_prefix (str): Label key prefix, matched as a substring of the key (e.g. "feature.node").

        Returns:
            int: total number of labels across all nodes whose key contains the prefix.
        """
        return self.get_node_labels_list().get_count_all_nodes_by_prefix(label_prefix)

    def count_labels_on_node_by_prefix(self, node_name: str, label_prefix: str) -> int:
        """Count labels on a single node whose key matches a prefix.

        Lists the node's labels with ``kubectl label node --list <node_name>`` and
        counts the matching keys on the ``KubectlLabelNodeListOutput`` object.

        Args:
            node_name (str): Name of the node to inspect.
            label_prefix (str): Label key prefix, matched as a substring of the key (e.g. "feature.node").

        Returns:
            int: number of labels on the node whose key contains the prefix.
        """
        return self.get_node_labels_list(node_name).get_count_on_node_by_prefix(node_name, label_prefix)

    def get_label_keys_on_node_by_prefix(self, node_name: str, label_prefix: str) -> list[str]:
        """List the label keys on a single node whose key matches a prefix.

        Lists the node's labels with ``kubectl label node --list <node_name>`` and
        filters the keys on the ``KubectlLabelNodeListOutput`` object. The returned
        keys are ready to be passed back to remove_label.

        Args:
            node_name (str): Name of the node to inspect.
            label_prefix (str): Label key prefix, matched as a substring of the key (e.g. "feature.node").

        Returns:
            list[str]: label keys on the node whose key contains the prefix.
        """
        return self.get_node_labels_list(node_name).get_label_keys_on_node_by_prefix(node_name, label_prefix)

    def remove_labels_on_node_by_prefix(self, node_name: str, label_prefix: str) -> int:
        """Remove all labels on a node whose key matches a prefix, in a single pass.

        Reads the matching label keys from ``kubectl label node --list``, removes
        each one, then returns how many still remain on the node. The remaining
        count lets callers retry (for example when a controller re-reconciles
        labels while its pods run).

        Args:
            node_name (str): Name of the node whose labels are removed.
            label_prefix (str): Label key prefix, matched as a substring of the key (e.g. "feature.node").

        Returns:
            int: the number of matching labels still present on the node after the removal pass.
        """
        feature_labels = self.get_label_keys_on_node_by_prefix(node_name, label_prefix)
        for label_key in feature_labels:
            self.remove_label(node_name, label_key)
        return self.count_labels_on_node_by_prefix(node_name, label_prefix)

    def remove_labels_all_nodes_by_prefix(self, label_prefix: str) -> int:
        """Remove all labels whose key matches a prefix from every node in the cluster, in a single pass.

        Lists every node's labels with a single ``kubectl label node --list --all``
        call, removes the matching keys node by node, then returns the total
        number of matching labels still present across the whole cluster. The
        remaining count lets callers assert the deletion worked or retry.

        Args:
            label_prefix (str): Label key prefix, matched as a substring of the key (e.g. "feature.node").

        Returns:
            int: total number of matching labels still present across all nodes after the removal pass.
        """
        labels_output = self.get_node_labels_list()
        for node_name in labels_output.get_node_names():
            label_keys = labels_output.get_label_keys_on_node_by_prefix(node_name, label_prefix)
            get_logger().log_info(f"Deleting {len(label_keys)} labels matching '{label_prefix}' from {node_name}")
            for label_key in label_keys:
                self.remove_label(node_name, label_key)
        return self.count_labels_all_nodes_by_prefix(label_prefix)

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
        # When no node matches, jsonpath prints nothing (or "[]"); both mean "no nodes".
        cmd = f"kubectl get nodes -l {label_key}={label_value} -o jsonpath='{{.items[*].metadata.name}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        names_str = "\n".join(output) if isinstance(output, list) else str(output)
        # Node names never contain shell/jsonpath punctuation. Filter to plausible
        # node-name tokens so the echoed command line and an empty "[]" result do
        # not get mistaken for a real node.
        tokens = [token for token in names_str.split() if token and not any(char in token for char in "[]{}=/'")]
        return tokens
