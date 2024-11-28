from keywords.k8s.pods.object.kubectl_get_pods_table_parser import KubectlGetPodsTableParser
from keywords.k8s.pods.object.kubectl_pod_object import KubectlPodObject


class KubectlGetPodsOutput:

    def __init__(self, kubectl_get_pods_output: str):
        """
        Constructor

        Args:
            kubectl_get_pods_output: Raw string output from running a "kubectl get pods" command.

        """

        self.kubectl_pod: [KubectlPodObject] = []
        kubectl_get_pods_table_parser = KubectlGetPodsTableParser(kubectl_get_pods_output)
        output_values_list = kubectl_get_pods_table_parser.get_output_values_list()

        for pod_dict in output_values_list:

            if 'NAME' not in pod_dict:
                raise ValueError(f"There is no NAME associated with the pod: {pod_dict}")

            pod = KubectlPodObject(pod_dict['NAME'])

            if 'NAMESPACE' in pod_dict:
                pod.set_ready(pod_dict['NAMESPACE'])

            if 'READY' in pod_dict:
                pod.set_ready(pod_dict['READY'])

            if 'STATUS' in pod_dict:
                pod.set_status(pod_dict['STATUS'])

            if 'RESTARTS' in pod_dict:
                pod.set_restarts(pod_dict['RESTARTS'])

            if 'AGE' in pod_dict:
                pod.set_age(pod_dict['AGE'])

            if 'IP' in pod_dict:
                pod.set_ip(pod_dict['IP'])

            if 'NODE' in pod_dict:
                pod.set_node(pod_dict['NODE'])

            if 'NOMINATED NODE' in pod_dict:
                pod.set_nominated_node(pod_dict['NOMINATED NODE'])

            if 'READINESS GATES' in pod_dict:
                pod.set_readiness_gates(pod_dict['READINESS GATES'])

            self.kubectl_pod.append(pod)

    def get_pod(self, pod_name) -> KubectlPodObject:
        """
        This function will get the pod with the name specified from this get_pods_output.
        Args:
            pod_name: The name of the pod of interest.

        Returns: KubectlPodObject

        """
        for pod in self.kubectl_pod:
            if pod.get_name() == pod_name:
                return pod
        else:
            raise ValueError(f"There is no pod with the name {pod_name}.")

    def get_pods_start_with(self, starts_with) -> [KubectlPodObject]:
        """
        Returns list of pods that starts with 'starts_with'
        Args:
            starts_with - the str the pod name starts with
        Returns:

        """

        pods = list(filter(lambda pod: starts_with in pod.get_name(), self.kubectl_pod))
        return pods

    def get_pods(self) -> [KubectlPodObject]:
        """
        Gets all pods
        Returns:

        """
        return self.kubectl_pod
