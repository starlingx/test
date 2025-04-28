import time

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.pods.object.kubectl_get_pods_output import KubectlGetPodsOutput


class KubectlGetPodsKeywords(BaseKeyword):
    """
    Class for 'kubectl get pods' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the KubectlGetPodsKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
        """
        self.ssh_connection = ssh_connection

    def get_pods(self, namespace: str = None) -> KubectlGetPodsOutput:
        """
        Gets the k8s pods that are available using '-o wide'.

        Args:
            namespace(str, optional): The namespace to search for pods. If None, it will search in all namespaces.

        Returns:
            KubectlGetPodsOutput: An object containing the parsed output of the command.

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
        Gets the k8s pods that are available using '-o wide' for all namespaces.

        Returns:
            KubectlGetPodsOutput: An object containing the parsed output of the command.
        """
        kubectl_get_pods_output = self.ssh_connection.send(export_k8s_config("kubectl -o wide get pods --all-namespaces"))
        self.validate_success_return_code(self.ssh_connection)
        pods_list_output = KubectlGetPodsOutput(kubectl_get_pods_output)

        return pods_list_output

    def wait_for_pod_status(self, pod_name: str, expected_status: str, namespace: str = None, timeout: int = 600) -> bool:
        """
        Waits timeout amount of time for the given pod to be in the given status

        Args:
            pod_name (str): the pod name
            expected_status (str): the expected status
            namespace (str): the namespace
            timeout (int): the timeout in secs

        Returns:
            bool: True if the pod is in the expected status

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
            expected_statuses ([str]): list of expected statuses ex. ['Completed' , 'Running']
            timeout (int): the amount of time in seconds to wait

        Returns:
            bool: True if all expected statuses are met

        """
        pod_status_timeout = time.time() + timeout

        while time.time() < pod_status_timeout:
            pods = self.get_pods_all_namespaces().get_pods()
            not_ready_pods = list(filter(lambda pod: pod.get_status() not in expected_statuses, pods))
            if len(not_ready_pods) == 0:
                return True
            time.sleep(5)

        return False
    def wait_for_pods_to_reach_status(self, expected_status: str, pod_names: list, namespace: str = None, poll_interval: int = 5, timeout: int = 180) -> bool:
            """
            Waits timeout amount of time for the given pod in a namespace to be in the given status
            Args:
                expected_status (str): the expected status
                pod_names (list): the pod names
                namespace (str): the namespace
                poll_interval (int): the interval in secs to poll for status
                timeout (int): the timeout in secs

            Returns:
                bool: True if pod is in expected status else False

            """

            pod_status_timeout = time.time() + timeout

            while time.time() < pod_status_timeout:
                pods = self.get_pods(namespace).get_pods()
                not_ready_pods = list(filter(lambda pod: pod.get_name() in pod_names and pod.get_status() != expected_status, pods))
                if len(not_ready_pods) == 0:
                    return True
                time.sleep(poll_interval)

            raise KeywordException(f"Pods {pod_names} in namespace {namespace} did not reach status {expected_status} within {timeout} seconds")
        
