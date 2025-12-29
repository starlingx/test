import json
from typing import List, Optional

from framework.logging.automation_logger import get_logger
from keywords.k8s.node.object.kubectl_nodes_object import KubectlNodesObject


class KubectlNodesJSONOutput:
    """Output object for `kubectl get nodes -o json`.

    Parses the JSON output and provides methods to access allocatable resources
    in a structured way.
    """

    def __init__(self, raw_text: str):
        """Initialize the output object with the raw JSON text.

        Args:
            raw_text (str): Raw string returned by `kubectl get nodes -o json`.
        """
        self._raw_text = raw_text
        parsed_json = self._parse_json(raw_text)
        items = parsed_json.get("items", []) if isinstance(parsed_json, dict) else []
        self.nodes = [self.build_kubectl_nodes_object_from_dict(item) for item in items]


    def _parse_json(self, text: str) -> dict:
        """Parse raw JSON text into a Python dictionary.

        If parsing fails, logs a warning and returns an empty dict.

        Args:
            text (str): Raw  JSON string.

        Returns:
            dict: Parsed JSON as a Python dictionary, or `{}` if parsing fails.
        """
        try:
            return json.loads(text)
        except Exception as e:
            get_logger().log_warning(f"Failed to parse JSON from kubectl get nodes: {e}")
            return {}

    def count_resource_total(self, resource_key: str) -> int:
        """Return the total sum of a given allocatable resource across all nodes.

        Args:
            resource_key (str): Resource key, e.g. `"dsa.intel.com/wq-user-dedicated"`.

        Returns:
            int: Total sum across all nodes (non-integer values are ignored).
        """
        total = 0
        for node_obj in self.get_node_objects():
            total += node_obj.get_allocatable_resource(resource_key)
        return total

    def get_node_resource(self, node_name: str, resource_key: str) -> int:
        """Return the allocatable resource value for a specific node.

        Args:
            node_name (str): Node name.
            resource_key (str): Resource key.

        Returns:
            int: Resource value for the node, or `0` if missing/non-integer.
        """
        node_obj = self.get_node_by_name(node_name)
        if node_obj:
            return node_obj.get_allocatable_resource(resource_key)
        return 0

    def get_node_objects(self) -> List[KubectlNodesObject]:
        """Return a list of `KubectlNodesObject` populated from the JSON items.

        Returns:
            List[KubectlNodesObject]: Structured node objects.
        """
        return self.nodes

    def get_node_by_name(self, name: str) -> Optional[KubectlNodesObject]:
        """Return a `KubectlNodesObject` by node name, or `None` if not found.

        Args:
            name (str): Node name to search.

        Returns:
            Optional[KubectlNodesObject]: Node object if found, otherwise `None`.
        """
        return next((obj for obj in self.nodes if obj.get_name() == name), None)


    def has_dedicated_queues(self) -> bool:
        """Return True if there is at least one dedicated DSA queue across all nodes.

        Returns:
            bool: `True` if any `dsa.intel.com/wq-user-dedicated` is present; otherwise `False`.
        """
        return self.count_resource_total("dsa.intel.com/wq-user-dedicated") > 0

    def has_shared_queues(self) -> bool:
        """Return True if there is at least one shared DSA queue across all nodes.

        Returns:
            bool: `True` if any `dsa.intel.com/wq-user-shared` is present; otherwise `False`.
        """
        return self.count_resource_total("dsa.intel.com/wq-user-shared") > 0

    def build_kubectl_nodes_object_from_dict(self, item: dict) -> "KubectlNodesObject":
        """Factory that builds a KubectlNodesObject from a single entry of 'kubectl get nodes -o json' (i.e., an element from .items[]).

        Field mapping:
        - name: metadata.name
        - status: derived from conditions (Ready=True -> 'Ready', otherwise 'NotReady'; 'Unknown' if missing)
        - roles: inferred from common role labels (joined as a comma-separated string)
        - age: not present in JSON (left as None)
        - version: status.nodeInfo.kubeletVersion
        """
        obj = KubectlNodesObject()
        # name
        name = (item.get("metadata") or {}).get("name")
        obj.set_name(name)

        # status (from conditions)
        status = "Unknown"
        conditions = (item.get("status") or {}).get("conditions") or []
        for cond in conditions:
            if cond.get("type") == "Ready":
                status = "Ready" if cond.get("status") == "True" else "NotReady"
                break
        obj.set_status(status)

        # roles
        labels = (item.get("metadata") or {}).get("labels") or {}
        roles_list = self._infer_roles_from_labels(labels)
        obj.set_roles(",".join(roles_list) if roles_list else None)

        # age (not available in JSON)
        obj.set_age(None)

        # version (kubeletVersion)
        node_info = (item.get("status") or {}).get("nodeInfo") or {}
        version = node_info.get("kubeletVersion")
        obj.set_version(version)

        # allocatable
        allocatable = (item.get("status") or {}).get("allocatable") or {}
        obj.set_allocatable(allocatable)

        return obj

    def _infer_roles_from_labels(self, labels: dict) -> list:
        """
        Role inference based on common Kubernetes node role labels.
        """
        roles = []
        if "node-role.kubernetes.io/control-plane" in labels:
            roles.append("control-plane")
        if "node-role.kubernetes.io/master" in labels:
            roles.append("master")
        if "node-role.kubernetes.io/worker" in labels:
            roles.append("worker")
        return roles
