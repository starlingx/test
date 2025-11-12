from typing import Union

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.pods.object.kubectl_get_pods_table_parser import KubectlGetPodsTableParser
from keywords.k8s.pods.object.kubectl_pod_object import KubectlPodObject


class KubectlGetPodsOutput:
    """A class to interact with and retrieve information about Kubernetes pods.

    This class provides methods to filter and retrieve pod information
    using the kubectl command output.
    """

    def __init__(self, kubectl_get_pods_output: Union[str, list[str]]):
        """Constructor.

        Args:
            kubectl_get_pods_output (Union[str, list[str]]): Raw output from running a kubectl get pods command.
        """
        self.kubectl_pod: list[KubectlPodObject] = []
        kubectl_get_pods_table_parser = KubectlGetPodsTableParser(kubectl_get_pods_output)
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
