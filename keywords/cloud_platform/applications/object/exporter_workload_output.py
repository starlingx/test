"""Exporter scheduling and readiness evidence independent of discovered pods."""


class ExporterWorkloadOutput:
    """Resolve eligible nodes from the rendered DaemonSet and node inventory."""

    def __init__(self, daemonset: dict, nodes: list[dict]):
        """Capture a Kubernetes scheduling snapshot.

        Args:
            daemonset (dict): Rendered exporter DaemonSet.
            nodes (list[dict]): Complete Kubernetes node inventory.
        """
        self.daemonset = daemonset
        self.nodes = nodes

    def get_label_selector(self) -> str:
        """Return the validated label selector used to query exporter pods.

        Returns:
            str: Comma-separated Kubernetes equality selectors.
        """
        selector = self.daemonset["spec"]["selector"]
        if selector.get("matchExpressions") or not selector.get("matchLabels"):
            raise ValueError("Exporter requires a nonempty matchLabels selector")
        return ",".join(f"{key}={value}" for key, value in sorted(selector["matchLabels"].items()))

    def eligible_nodes(self) -> tuple[str, ...]:
        """Evaluate supported scheduling constraints without deriving coverage from pods.

        Unsupported affinity is rejected explicitly before consumers mutate state.

        Returns:
            tuple[str, ...]: Nonempty unique eligible node names.
        """
        spec = self.daemonset["spec"]["template"]["spec"]
        if spec.get("affinity") or spec.get("nodeName") or spec.get("schedulerName", "default-scheduler") != "default-scheduler":
            raise ValueError("Exporter scheduling uses unsupported affinity, nodeName or scheduler")
        selector = spec.get("nodeSelector", {})
        if not isinstance(selector, dict):
            raise ValueError("Invalid exporter nodeSelector")
        eligible_node_names = []
        seen_node_names = set()
        automatically_tolerated_taint_keys = {"node.kubernetes.io/not-ready", "node.kubernetes.io/unreachable", "node.kubernetes.io/disk-pressure", "node.kubernetes.io/memory-pressure", "node.kubernetes.io/pid-pressure", "node.kubernetes.io/unschedulable"}
        if spec.get("hostNetwork"):
            automatically_tolerated_taint_keys.add("node.kubernetes.io/network-unavailable")
        for node in self.nodes:
            name = node["metadata"]["name"]
            if not name or name in seen_node_names:
                raise ValueError("Missing or duplicate node identity")
            seen_node_names.add(name)
            if not selector.items() <= node["metadata"].get("labels", {}).items():
                continue
            has_untolerated_taint = False
            for taint in node.get("spec", {}).get("taints", []):
                if taint.get("effect") not in ("NoSchedule", "NoExecute") or taint["key"] in automatically_tolerated_taint_keys:
                    continue
                taint_is_tolerated = any((not item.get("effect") or item["effect"] == taint["effect"]) and (item.get("key", "") == taint["key"] or (not item.get("key") and item.get("operator") == "Exists")) and (item.get("operator", "Equal") == "Exists" or item.get("value", "") == taint.get("value", "")) for item in spec.get("tolerations", []))
                has_untolerated_taint |= not taint_is_tolerated
            if not has_untolerated_taint:
                eligible_node_names.append(name)
        if not eligible_node_names:
            raise ValueError("No eligible exporter nodes in rendered scheduling and inventory")
        return tuple(sorted(eligible_node_names))

    def ready_pods(self, pods: list[dict]) -> dict[str, dict]:
        """Require one current ready DaemonSet pod per independently eligible node.

        Args:
            pods (list[dict]): Pods selected using the DaemonSet label selector.

        Returns:
            dict[str, dict]: Ready pods by node, or empty during convergence.
        """
        expected_node_names = set(self.eligible_nodes())
        daemonset_generation = self.daemonset["metadata"].get("generation")
        rollout_status = self.daemonset.get("status", {})
        if type(daemonset_generation) is not int or daemonset_generation < 1 or rollout_status.get("observedGeneration") != daemonset_generation:
            return {}
        # Controller status identifies the current template, including changes
        # that keep the same image. A DaemonSet UID alone does not identify it.
        expected_node_count = len(expected_node_names)
        if any(rollout_status.get(field) != expected_node_count for field in ("desiredNumberScheduled", "currentNumberScheduled", "updatedNumberScheduled", "numberReady", "numberAvailable")):
            return {}
        if rollout_status.get("numberMisscheduled", 0) != 0:
            return {}
        ready_pods_by_node = {}
        pod_revision_hashes = set()
        daemonset_uid = self.daemonset["metadata"]["uid"]
        for pod in pods:
            metadata, spec, status = pod["metadata"], pod["spec"], pod.get("status", {})
            if not any(owner.get("uid") == daemonset_uid and owner.get("controller") is True for owner in metadata.get("ownerReferences", [])):
                raise ValueError("Exporter selector matched a pod outside the selected DaemonSet")
            revision_hash = metadata.get("labels", {}).get("controller-revision-hash")
            if not revision_hash:
                return {}
            pod_revision_hashes.add(revision_hash)
            if len(pod_revision_hashes) != 1:
                return {}
            node = spec.get("nodeName")
            expected_container_names = {item["name"] for item in spec.get("containers", [])}
            container_statuses = status.get("containerStatuses", [])
            if not node or node in ready_pods_by_node or node not in expected_node_names or metadata.get("deletionTimestamp") or not metadata.get("uid"):
                return {}
            if status.get("phase") != "Running" or not any(item.get("type") == "Ready" and item.get("status") == "True" for item in status.get("conditions", [])):
                return {}
            if not expected_container_names or len(container_statuses) != len(expected_container_names) or {item["name"] for item in container_statuses} != expected_container_names:
                return {}
            if not all(item.get("ready") is True and "running" in item.get("state", {}) for item in container_statuses):
                return {}
            ready_pods_by_node[node] = pod
        return ready_pods_by_node if set(ready_pods_by_node) == expected_node_names else {}
