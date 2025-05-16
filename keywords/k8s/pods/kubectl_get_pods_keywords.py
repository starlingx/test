import time

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
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
        
    def get_pods(self, namespace: str = None, label: str = None) -> KubectlGetPodsOutput:
        """
        Gets the k8s pods that are available using '-o wide'.

        Args:
            namespace(str, optional): The namespace to search for pods. If None, it will search in all namespaces.
            label (str, optional): The label to search for pods.

        Returns:
            KubectlGetPodsOutput: An object containing the parsed output of the command.

        """
        arg_namespace = ""

        arg_label = ""

        if namespace:
            arg_namespace = f"-n {namespace}"

        if label:
            arg_label = f"-l {label}"

        kubectl_get_pods_output = self.ssh_connection.send(export_k8s_config(f"kubectl {arg_namespace} {arg_label} -o wide get pods"))
        self.validate_success_return_code(self.ssh_connection)
        pods_list_output = KubectlGetPodsOutput(kubectl_get_pods_output)

        return pods_list_output
    
    def get_pods_no_validation(self, namespace: str = None) -> KubectlGetPodsOutput:
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
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            return None
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

    def wait_for_pod_max_age(self, pod_name: str, max_age: int, namespace: str = None, timeout: int = 600, check_interval: int = 20) -> bool:
        """
        Waits for the pod to be in a certain max_age.

        Args:
            pod_name (str): the pod name
            max_age (int): the max age in minutes
            namespace (str): the namespace
            timeout (int): the timeout in seconds
            check_interval (int): the interval between checks in seconds

        Returns:
            bool: True if the pod's age became max_age
        """
        end_time = time.time() + timeout

        while time.time() < end_time:
            pods_output = self.get_pods_no_validation(namespace)
            if not pods_output:
                time.sleep(check_interval)
                continue
            pod_age_in_minutes = pods_output.get_pod(pod_name).get_age_in_minutes()
            if pod_age_in_minutes == max_age:
                return True
            time.sleep(check_interval)

        raise Exception(f"The pod {pod_name} did not reach the age {max_age}")

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
            pods_output = self.get_pods_no_validation()
            if pods_output:
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

    def wait_for_pods_to_reach_status(self, expected_status: str, pod_names: list = None, namespace: str = None, poll_interval: int = 5, timeout: int = 180) -> bool:
        """
        Waits timeout amount of time for the given pod in a namespace to be in the given status

        Args:
            expected_status (str): the expected status
            pod_names (list): the pod names to look for. If left as None, we will check for all the pods.
            namespace (str): the namespace
            poll_interval (int): the interval in secs to poll for status
            timeout (int): the timeout in secs

        Returns:
            bool: True if pod is in expected status else False

        """
        pod_status_timeout = time.time() + timeout

        while time.time() < pod_status_timeout:

            pods = self.get_pods(namespace).get_pods()

            # We need to filter the list for only the pods matching the pod names if specified
            if pod_names:
                pods = [pod for pod in pods if pod.get_name() in pod_names]

            pods_in_incorrect_status = [pod for pod in pods if pod.get_status() != expected_status]

            if len(pods_in_incorrect_status) == 0:
                return True
            time.sleep(poll_interval)
        pods_in_incorrect_status_names = [pod.get_name() for pod in pods_in_incorrect_status]
        pods_in_incorrect_status_names = ", ".join(pods_in_incorrect_status_names)
        raise KeywordException(f"Pods {pods_in_incorrect_status_names} in namespace {namespace} did not reach status {expected_status} within {timeout} seconds")

    def wait_for_kubernetes_to_restart(self, timeout: int = 600, check_interval: int = 20) -> bool:
        """
        Wait for the Kubernetes API to go down, then wait for the kube-apiserver pod to be Running.

        Args:
            timeout (int): Maximum time to wait in seconds.
            check_interval (int): Time between checks in seconds.

        Returns:
            bool: True if Kubernetes restarted and kube-apiserver pod becomes Running.

        Raises:
            TimeoutError: If the Kubernetes API doesn't restart properly.
        """

        def is_kubernetes_up() -> bool:
            output = self.ssh_connection.send(export_k8s_config("kubectl get pods -A"))
            return "was refused - did you specify the right host or port?" not in output[0]

        validate_equals_with_retry(
            function_to_execute=is_kubernetes_up,
            expected_value=False,
            validation_description="Kubernetes is down for a restart",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )

        validate_equals_with_retry(
            function_to_execute=is_kubernetes_up,
            expected_value=True,
            validation_description="Kubernetes is back up after the restart",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )

        self.wait_for_pod_status(pod_name="kube-apiserver-controller-0", expected_status="Running", namespace="kube-system", timeout=timeout)

        return self.wait_for_pod_max_age(pod_name="kube-apiserver-controller-0", max_age=3, namespace="kube-system", timeout=timeout)
