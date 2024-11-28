import time

from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.pods.object.kubectl_get_pods_output import KubectlGetPodsOutput


class KubectlGetPodsKeywords(BaseKeyword):
    """
    Class for 'kubectl get pods' keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_pods(self, namespace: str = None) -> KubectlGetPodsOutput:
        """
        Gets the k8s pods that are available using '-o wide'.
        Args:
            namespace ():

        Returns:

        """

        arg_namespace = ""
        if namespace:
            arg_namespace = f"-n {namespace}"

        kubectl_get_pods_output = self.ssh_connection.send(export_k8s_config(f"kubectl {arg_namespace} -o wide get pods"))
        self.validate_success_return_code(self.ssh_connection)
        pods_list_output = KubectlGetPodsOutput(kubectl_get_pods_output)

        return pods_list_output

    def get_pods_all_namespaces(self) -> KubectlGetPodsOutput:
        """
        Gets the k8s pods that are available using '-o wide'.
        Args:
            namespace ():

        Returns:

        """

        kubectl_get_pods_output = self.ssh_connection.send(export_k8s_config("kubectl -o wide get pods --all-namespaces"))
        self.validate_success_return_code(self.ssh_connection)
        pods_list_output = KubectlGetPodsOutput(kubectl_get_pods_output)

        return pods_list_output

    def wait_for_pod_status(self, pod_name: str, expected_status: str, namespace: str = None, timeout: int = 600) -> bool:
        """
        Waits timeout amount of time for the given pod to be in the given status
        Args:
            pod_name (): the pod name
            expected_status (): the expected status
            namespace (): the namespace
            timeout (): the timeout in secs

        Returns:

        """

        pod_status_timeout = time.time() + timeout

        while time.time() < pod_status_timeout:
            pod_status = self.get_pods(namespace).get_pod(pod_name).get_status()
            if pod_status == expected_status:
                return True
            time.sleep(5)

        return False

    def wait_for_all_pods_status(self, expected_statuses: [str], timeout: int = 600) -> bool:
        """
        Wait for all pods to be in the given status(s)
        Args:
            expected_statuses (): list of expected statuses ex. ['Completed' , 'Running']
            timeout (): the amount of time in seconds to wait

        Returns: True if all expected statuses are met

        """
        pod_status_timeout = time.time() + timeout

        while time.time() < pod_status_timeout:
            pods = self.get_pods_all_namespaces().get_pods()
            not_ready_pods = list(filter(lambda pod: pod.get_status() not in expected_statuses, pods))
            if len(not_ready_pods) == 0:
                return True
            time.sleep(5)

        return False
