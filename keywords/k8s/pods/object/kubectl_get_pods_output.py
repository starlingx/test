import json
from typing import Union

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.pods.object.kubectl_get_pods_table_parser import KubectlGetPodsTableParser
from keywords.k8s.pods.object.kubectl_pod_object import KubectlPodObject


class KubectlGetPodsOutput:
    """A class to interact with and retrieve information about Kubernetes pods.

    This class provides methods to filter and retrieve pod information
    using the kubectl command output. Supports both table and JSON sources.
    """

    ALLOWED_SOURCES = {"table", "json"}

    def __init__(self, kubectl_get_pods_output: Union[str, list[str]], source: str = "table"):
        """Constructor.

        Args:
            kubectl_get_pods_output (Union[str, list[str]]): Raw output from running a kubectl get pods command.
            source (str): Data source format ('table' or 'json'). Defaults to 'table'.
        """
        if source not in self.ALLOWED_SOURCES:
            raise ValueError(f"Invalid source '{source}'. Allowed sources: {sorted(self.ALLOWED_SOURCES)}")

        self.source = source
        self.kubectl_pod: list[KubectlPodObject] = []

        if source == "table":
            self._parse_table(kubectl_get_pods_output)
        elif source == "json":
            self._parse_json(kubectl_get_pods_output)

    def _parse_table(self, raw_output: Union[str, list[str]]) -> None:
        """Parse kubectl table output into pod objects.

        Args:
            raw_output (Union[str, list[str]]): Raw table output from kubectl get pods.
        """
        kubectl_get_pods_table_parser = KubectlGetPodsTableParser(raw_output)
        output_values_list = kubectl_get_pods_table_parser.get_output_values_list()

        for pod_dict in output_values_list:

            if "NAME" not in pod_dict:
                raise KeywordException(f"There is no NAME associated with the pod: {pod_dict}")

            pod = KubectlPodObject(pod_dict["NAME"])

            if "NAMESPACE" in pod_dict:
                pod.set_namespace(pod_dict["NAMESPACE"])

            if "READY" in pod_dict:
                pod.set_ready(pod_dict["READY"])

            if "STATUS" in pod_dict:
                pod.set_status(pod_dict["STATUS"])

            if "RESTARTS" in pod_dict:
                pod.set_restarts(pod_dict["RESTARTS"])

            if "AGE" in pod_dict:
                pod.set_age(pod_dict["AGE"])

            if "IP" in pod_dict:
                pod.set_ip(pod_dict["IP"])

            if "NODE" in pod_dict:
                pod.set_node(pod_dict["NODE"])

            if "NOMINATED NODE" in pod_dict:
                pod.set_nominated_node(pod_dict["NOMINATED NODE"])

            if "READINESS GATES" in pod_dict:
                pod.set_readiness_gates(pod_dict["READINESS GATES"])

            self.kubectl_pod.append(pod)

    def _parse_json(self, raw_output: Union[str, list[str]]) -> None:
        """Parse kubectl JSON output into pod objects.

        Args:
            raw_output (Union[str, list[str]]): Raw JSON output from kubectl get pods -o json.
        """
        raw_str = "\n".join(raw_output) if isinstance(raw_output, list) else raw_output
        data = json.loads(raw_str)
        items = data.get("items", [])
        for item in items:
            pod = self._build_pod_from_json(item)
            self.kubectl_pod.append(pod)

    def _build_pod_from_json(self, item: dict) -> KubectlPodObject:
        """Build a KubectlPodObject from a single JSON item.

        Args:
            item (dict): A single pod item from kubectl get pods -o json.

        Returns:
            KubectlPodObject: Parsed pod object.
        """
        metadata = item.get("metadata", {})
        status_data = item.get("status", {})
        spec = item.get("spec", {})

        pod = KubectlPodObject(metadata.get("name", ""))
        pod.set_namespace(metadata.get("namespace"))
        pod.set_status(status_data.get("phase", ""))
        pod.set_ip(status_data.get("podIP"))
        pod.set_node(spec.get("nodeName"))

        # Extract container images
        containers = spec.get("containers", [])
        images = [c.get("image", "") for c in containers if c.get("image")]
        pod.set_images(images)

        # Ready count from containerStatuses
        container_statuses = status_data.get("containerStatuses", [])
        ready_count = sum(1 for cs in container_statuses if cs.get("ready"))
        total_count = len(container_statuses) if container_statuses else len(containers)
        pod.set_ready(f"{ready_count}/{total_count}")

        return pod

    def get_pod(self, pod_name: str) -> KubectlPodObject:
        """Get the pod with the name specified from this get_pods_output.

        Args:
            pod_name (str): The name of the pod of interest.

        Returns:
            KubectlPodObject: The pod object with the name specified.

        Raises:
            KeywordException: If the pod with the specified name does not exist in the output.
        """
        for pod in self.kubectl_pod:
            if pod.get_name() == pod_name:
                return pod
        raise KeywordException(f"There is no pod with the name {pod_name}.")

    def get_pods_start_with(self, starts_with: str) -> list[KubectlPodObject]:
        """Return list of pods that starts with specified string.

        Args:
            starts_with (str): The string the pod name starts with.

        Returns:
            list[KubectlPodObject]: List of pods that starts with specified string.
        """
        pods = list(filter(lambda pod: starts_with in pod.get_name(), self.kubectl_pod))
        return pods

    def get_single_pod_start_with(self, starts_with: str, status: str = None) -> KubectlPodObject:
        """Get single pod that starts with specified string and optionally matches status.

        Args:
            starts_with (str): The string the pod name starts with.
            status (str, optional): Filter by pod status (e.g., "Running"). Defaults to None.

        Returns:
            KubectlPodObject: The pod object if exactly one match found.

        Raises:
            KeywordException: If zero or multiple pods match the criteria.
        """
        pods = self.get_pods_start_with(starts_with)
        if status:
            pods = [p for p in pods if p.get_status() == status]
        if len(pods) != 1:
            raise KeywordException(f"Expected exactly 1 pod starting with '{starts_with}', found {len(pods)}.")
        return pods[0]

    def get_pods(self) -> list[KubectlPodObject]:
        """Get all pods.

        Returns:
            list[KubectlPodObject]: A list of all pods.
        """
        return self.kubectl_pod

    def get_unique_pod_matching_prefix(self, starts_with: str) -> str:
        """Get the full name of pod that starts with the given prefix.

        Args:
            starts_with (str): The prefix of the pod name.

        Returns:
            str: Pod name if one pod matches.

        Raises:
            KeywordException: If no pods match the prefix.
        """
        pods = self.get_pods_start_with(starts_with)
        if len(pods) == 0:
            raise KeywordException(f"No pods found starting with '{starts_with}'.")
        return pods[0].get_name()

    def get_pods_with_status(self, status: str) -> list[KubectlPodObject]:
        """Return list of pods with the specified status.

        Args:
            status (str): The status to filter by (e.g., "Running", "Pending").

        Returns:
            list[KubectlPodObject]: List of pods with the specified status.
        """
        return [pod for pod in self.kubectl_pod if pod.get_status() == status]

    def get_pods_on_node(self, node_name: str) -> list[KubectlPodObject]:
        """Get list of pod objects running on a specific node.

        Args:
            node_name (str): Name of the node.

        Returns:
            list[KubectlPodObject]: List of pod objects on the specified node.
        """
        return [pod for pod in self.kubectl_pod if pod.get_node() == node_name]

    def get_all_container_images(self) -> list[str]:
        """Get all container images across all pods.

        Returns:
            list[str]: List of container image strings from all pods.
        """
        images = []
        for pod in self.kubectl_pod:
            images.extend(pod.get_images())
        return images
