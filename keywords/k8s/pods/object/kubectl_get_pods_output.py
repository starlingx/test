from keywords.k8s.pods.object.kubectl_get_pods_table_parser import KubectlGetPodsTableParser
from keywords.k8s.pods.object.kubectl_pod_object import KubectlPodObject


class KubectlGetPodsOutput:
    """
    A class to interact with and retrieve information about Kubernetes pods.

    This class provides methods to filter and retrieve pod information
    using the `kubectl` command output.
    """

    def __init__(self, kubectl_get_pods_output: str):
        """
        Constructor

        Args:
            kubectl_get_pods_output (str): Raw string output from running a "kubectl get pods" command.
        """
        self.kubectl_pod: [KubectlPodObject] = []
        kubectl_get_pods_table_parser = KubectlGetPodsTableParser(kubectl_get_pods_output)
        output_values_list = kubectl_get_pods_table_parser.get_output_values_list()

        for pod_dict in output_values_list:

            if "NAME" not in pod_dict:
                raise ValueError(f"There is no NAME associated with the pod: {pod_dict}")

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
        """
        This function will get the pod with the name specified from this get_pods_output.

        Args:
            pod_name (str): The name of the pod of interest.

        Returns:
            KubectlPodObject: The pod object with the name specified.

        Raises:
            ValueError: If the pod with the specified name does not exist in the output.
        """
        for pod in self.kubectl_pod:
            if pod.get_name() == pod_name:
                return pod
        else:
            raise ValueError(f"There is no pod with the name {pod_name}.")

    def get_pods_start_with(self, starts_with: str) -> [KubectlPodObject]:
        """
        Returns list of pods that starts with 'starts_with'

        Args:
            starts_with (str): the str the pod name starts with

        Returns:
            [KubectlPodObject]: list of pods that starts with 'starts_with'

        """
        pods = list(filter(lambda pod: starts_with in pod.get_name(), self.kubectl_pod))
        return pods

    def get_pods(self) -> [KubectlPodObject]:
        """
        Gets all pods.

        Returns:
            [KubectlPodObject]: A list of all pods.

        """
        return self.kubectl_pod

    def get_unique_pod_matching_prefix(self, starts_with: str) -> str:
        """
        Get the full name(s) of pod(s) that start with the given prefix.

        Args:
            starts_with(str): The prefix of the pod name.

        Returns:
            str: A string if one pod matches

        Raises:
            ValueError: If no pods match the prefix.
        """
        pods = self.get_pods_start_with(starts_with)
        if len(pods) == 0:
            raise ValueError(f"No pods found starting with '{starts_with}'.")
        return pods[0].get_name()

    def get_pods_with_status(self, status: str) -> [KubectlPodObject]:
        """
        Returns list of pods with the specified status.

        Args:
            status (str): The status to filter by (e.g., "Running", "Pending").

        Returns:
            [KubectlPodObject]: List of pods with the specified status.
        """
        return [pod for pod in self.kubectl_pod if pod.get_status() == status]
