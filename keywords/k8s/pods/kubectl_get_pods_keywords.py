import json
import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.object.kubectl_get_pods_output import KubectlGetPodsOutput


class KubectlGetPodsKeywords(K8sBaseKeyword):
    """
    Class for 'kubectl get pods' keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Initialize the KubectlGetPodsKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_pods(self, namespace: str = None, label: str = None) -> KubectlGetPodsOutput:
        """Gets the k8s pods that are available using '-o wide'.

        Args:
            namespace (str, optional): The namespace to search for pods. If None, it will search in all namespaces.
            label (str, optional): The label to search for pods.

        Returns:
            KubectlGetPodsOutput: An object containing the parsed output of the command.
        """
        arg_namespace = ""

        arg_all_namespaces = ""

        arg_label = ""

        if namespace:
            arg_namespace = f"-n {namespace}"
        else:
            arg_all_namespaces = "--all-namespaces"

        if label:
            arg_label = f"-l {label}"

        cmd = f"kubectl {arg_namespace} {arg_label} -o wide get pods {arg_all_namespaces}"

        kubectl_get_pods_output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        pods_list_output = KubectlGetPodsOutput(kubectl_get_pods_output)

        return pods_list_output

    def get_pods_no_validation(self, namespace: str = None) -> KubectlGetPodsOutput:
        """
        Get the k8s pods that are available using '-o wide'.

        Args:
            namespace (str, optional): The namespace to search for pods. If None, it will search in
        all namespaces.

        Returns:
            KubectlGetPodsOutput: An object containing the parsed output of the command.
        """

        # If namespace is None, search for all namespaces.
        if namespace:
            arg_namespace = f"-n {namespace}"
        else:
            arg_namespace = "--all-namespaces"

        kubectl_get_pods_output = self.ssh_connection.send(self.k8s_config.export(f"kubectl -o wide get pods {arg_namespace}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            return None
        pods_list_output = KubectlGetPodsOutput(kubectl_get_pods_output)

        return pods_list_output

    def get_pods_all_namespaces(self) -> KubectlGetPodsOutput:
        """
        Get the k8s pods that are available using '-o wide' for all namespaces.

        Returns:
            KubectlGetPodsOutput: An object containing the parsed output of the command.
        """
        kubectl_get_pods_output = self.ssh_connection.send(self.k8s_config.export("kubectl -o wide get pods --all-namespaces"))
        self.validate_success_return_code(self.ssh_connection)
        pods_list_output = KubectlGetPodsOutput(kubectl_get_pods_output)

        return pods_list_output

    def get_unhealthy_pods(self) -> KubectlGetPodsOutput:
        """
        Get the k8s pods that are unhealthy

        Returns:
            KubectlGetPodsOutput: An object containing the parsed output of the command.
        """
        field_selector = "status.phase!=Running,status.phase!=Succeeded"
        kubectl_get_pods_output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get pods --all-namespaces --field-selector={field_selector}"))
        self.validate_success_return_code(self.ssh_connection)
        pods_list_output = KubectlGetPodsOutput(kubectl_get_pods_output)

        return pods_list_output

    def wait_for_pod_max_age(self, pod_name: str, max_age: int, namespace: str = None, timeout: int = 600, check_interval: int = 20) -> bool:
        """
        Wait for the pod to be in a certain max_age.

        Args:
            pod_name (str): the pod name.
            max_age (int): the max age in minutes.
            namespace (str): the namespace.
            timeout (int): the timeout in seconds.
            check_interval (int): the interval between checks in seconds.

        Returns:
            bool: True if the pod's age became max_age.
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
        """Wait timeout amount of time for the given pod to be in the given status.

        Args:
            pod_name (str): The pod name.
            expected_status (str): The expected status.
            namespace (str): The namespace.
            timeout (int): The timeout in seconds.

        Returns:
            bool: True if the pod is in the expected status.
        """
        return self.wait_for_pods_to_reach_status(expected_status=expected_status, pod_names=[pod_name], namespace=namespace, timeout=timeout)

    def wait_for_all_pods_status(self, expected_statuses: list[str], timeout: int = 600) -> bool:
        """
        Wait for all pods to be in the given status(s)

        Args:

            expected_statuses (list[str]): list of expected statuses ex. ['Completed' , 'Running']
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

        raise KeywordException("All pods are not in the expected status")

    def wait_for_pods_to_reach_status(self, expected_status: str | list, pod_names: list = None, namespace: str = None, poll_interval: int = 10, timeout: int = 180) -> bool:
        """Wait for specified pods to reach expected status within timeout period.

        This function monitors pods in a given namespace and waits for them to reach
        one of the expected statuses. It can monitor specific pods by name or all pods
        in the namespace if no pod names are provided.

        Args:
            expected_status (str | list): Single status string or list of acceptable statuses
                                        (e.g., 'Running', ['Running', 'Completed']).
            pod_names (list, optional): List of specific pod names to monitor. If None,
                                      monitors all pods in the namespace. Defaults to None.
            namespace (str, optional): Kubernetes namespace to search in. If None, searches
                                     all namespaces. Defaults to None.
            poll_interval (int): Time in seconds between status checks. Defaults to 5.
            timeout (int): Maximum time in seconds to wait for pods to reach expected
                         status. Defaults to 180.

        Returns:
            bool: True if all specified pods reach expected status within timeout.

        Raises:
            KeywordException: If pods are not found within timeout or don't reach
                            expected status within timeout period.
        """
        pod_status_timeout = time.time() + timeout

        # Normalize expected_status to list for consistent processing
        if isinstance(expected_status, str):
            expected_statuses = [expected_status]
        else:
            expected_statuses = expected_status

        get_logger().log_info(f"Waiting for pods {pod_names} to reach {expected_statuses} status in namespace {namespace}")

        # Initialize pending pods - if no pod_names given, get all pods in namespace
        if pod_names:
            pending_pods = list(pod_names)
        else:
            initial_pods = self.get_pods(namespace).get_pods()
            pending_pods = [pod.get_name() for pod in initial_pods]

        while time.time() < pod_status_timeout:
            pods_output = self.get_pods_no_validation(namespace)
            if not pods_output:
                time.sleep(poll_interval)
                continue
            pods = pods_output.get_pods()
            # Check each pending pod
            for pod_name in pending_pods[:]:
                # Find pods matching the prefix (or exact name if no pod_names specified)
                matching_pods = [p for p in pods if p.get_name().startswith(pod_name)]

                # If all matching pods are in expected status, remove from pending list
                if matching_pods and all(p.get_status() in expected_statuses for p in matching_pods):
                    get_logger().log_debug(f"Pod {pod_name} reached {expected_statuses} status")
                    pending_pods.remove(pod_name)

            # If no pending pods remain, all have reached expected status
            if not pending_pods:
                get_logger().log_info(f"All pods reached {expected_statuses} status or were cleaned up")
                return True
            else:
                get_logger().log_debug(f"Pods left to reach status: {pending_pods}")

            time.sleep(poll_interval)

        # Timeout reached - raise exception with pending pods
        raise KeywordException(f"Pods {list(pending_pods)} did not reach {expected_statuses} status within {timeout} seconds")

    def get_pod_labels(self, pod_name: str, namespace: str = None) -> dict:
        """Get pod labels using kubectl JSONPath output.

        Args:
            pod_name (str): Name of the pod.
            namespace (str, optional): Namespace of the pod.

        Returns:
            dict: Pod labels as key-value pairs.
        """
        cmd = f"kubectl get pod {pod_name} -o jsonpath='{{.metadata.labels}}'"
        if namespace:
            cmd += f" -n {namespace}"

        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        content = "\n".join(output) if isinstance(output, list) else output
        if not content.strip():
            return {}

        return json.loads(content)

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
            output = self.ssh_connection.send(self.k8s_config.export("kubectl get pods -A"))
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
