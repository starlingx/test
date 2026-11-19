import re
from typing import Dict, List, Optional, Union


class KubectlLabelNodeListOutput:
    """Output object for 'kubectl label node --list' (one node) and 'kubectl label node --list --all' (every node).

    With ``--all`` the command prints one block per node, each starting with a header::

        Listing labels for Node./controller-0:
         feature.node.kubernetes.io/cpu-cpuid.AVX2=true
         feature.node.kubernetes.io/cpu-model.family=6

    When a single node is listed, the header is not printed and only the
    ``key=value`` lines are returned, so the node name must be given to the
    constructor (``default_node_name``).

    The raw text is parsed into a mapping of node name to its label key/value
    pairs, and the filtering/counting by prefix is done here, not in the shell.
    """

    _HEADER_PATTERN = re.compile(r"^Listing labels for .*?/(?P<name>[^/:\s]+):\s*$")

    def __init__(self, raw_output: Union[str, List[str]], default_node_name: Optional[str] = None):
        """Constructor.

        Args:
            raw_output (Union[str, List[str]]): Raw output (text or list of lines) of 'kubectl label node --list'.
            default_node_name (Optional[str]): Node the labels belong to when the output has no
                "Listing labels for ..." header (single-node listing). Defaults to None.
        """
        self._labels_by_node: Dict[str, Dict[str, str]] = {}
        text = "\n".join(raw_output) if isinstance(raw_output, list) else str(raw_output)

        current_node = default_node_name
        if current_node:
            self._labels_by_node[current_node] = {}

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            header = self._HEADER_PATTERN.match(line)
            if header:
                current_node = header.group("name")
                self._labels_by_node.setdefault(current_node, {})
            elif current_node and "=" in line:
                key, value = line.split("=", 1)
                self._labels_by_node[current_node][key] = value

    def get_node_names(self) -> List[str]:
        """Returns the names of the nodes present in the output.

        Returns:
            List[str]: Node names.
        """
        return list(self._labels_by_node.keys())

    def get_labels_on_node(self, node_name: str) -> Dict[str, str]:
        """Returns all labels of a node.

        Args:
            node_name (str): Name of the node.

        Returns:
            Dict[str, str]: Label key/value pairs, empty if the node is not in the output.
        """
        return self._labels_by_node.get(node_name, {})

    def get_label_keys_on_node_by_prefix(self, node_name: str, label_prefix: str) -> List[str]:
        """Returns the label keys of a node that contain the given prefix.

        Args:
            node_name (str): Name of the node.
            label_prefix (str): Substring to filter label keys by (e.g. "feature.node").

        Returns:
            List[str]: Matching label keys.
        """
        return [key for key in self.get_labels_on_node(node_name) if label_prefix in key]

    def get_count_on_node_by_prefix(self, node_name: str, label_prefix: str) -> int:
        """Returns how many labels of a node have a key containing the given prefix.

        Args:
            node_name (str): Name of the node.
            label_prefix (str): Substring to filter label keys by (e.g. "feature.node").

        Returns:
            int: Number of matching labels.
        """
        return len(self.get_label_keys_on_node_by_prefix(node_name, label_prefix))

    def get_count_all_nodes_by_prefix(self, label_prefix: str) -> int:
        """Returns how many labels across every node have a key containing the given prefix.

        Args:
            label_prefix (str): Substring to filter label keys by (e.g. "feature.node").

        Returns:
            int: Total number of matching labels across all nodes.
        """
        return sum(self.get_count_on_node_by_prefix(node_name, label_prefix) for node_name in self._labels_by_node)
