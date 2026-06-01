"""Keywords for Prometheus exporter pod operations via generic kubectl commands."""

from typing import List

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_get_pod_jsonpath_keywords import KubectlGetPodJsonpathKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class ExporterPodKeywords(K8sBaseKeyword):
    """Keywords for managing and validating exporter pods.

    Uses generic kubectl pod keywords internally. The namespace and label
    selector are configurable to support any Prometheus exporter deployment.
    """

    def __init__(
        self,
        ssh_connection: SSHConnection,
        namespace: str = "openstack",
        label: str = "application=prometheus-openstack-exporter",
    ) -> None:
        """Initialize ExporterPodKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
            namespace (str): Namespace where exporter pods run.
            label (str): Label selector for exporter pods.
        """
        super().__init__(ssh_connection)
        self._namespace = namespace
        self._label = label

    def get_exporter_pod_count(self) -> int:
        """Get the number of running exporter pods.

        Returns:
            int: Number of exporter pods in Running state.
        """
        pods_kw = KubectlGetPodsKeywords(self.ssh_connection)
        pods_output = pods_kw.get_pods(
            namespace=self._namespace,
            label=self._label,
        )
        pods = pods_output.get_pods()
        running_count = sum(1 for p in pods if p.get_status() == "Running")
        get_logger().log_info(f"Exporter pods running: {running_count}/{len(pods)}")
        return running_count

    def get_ready_pod_count(self) -> int:
        """Get the number of exporter pods that are Running and READY.

        A pod is READY when all containers have passed readiness probes
        (e.g. 1/1). This is more reliable than just Running (0/1) for
        determining when the exporter is actually serving metrics.

        Returns:
            int: Number of exporter pods in Running+READY state.
        """
        pods_kw = KubectlGetPodsKeywords(self.ssh_connection)
        pods_output = pods_kw.get_pods(
            namespace=self._namespace,
            label=self._label,
        )
        pods = pods_output.get_pods()
        ready_count = sum(1 for p in pods if p.get_status() == "Running" and p.is_ready())
        get_logger().log_info(f"Exporter pods ready: {ready_count}/{len(pods)}")
        return ready_count

    def get_exporter_pod_nodes(self) -> List[str]:
        """Get the node names where exporter pods are scheduled.

        Returns:
            List[str]: List of node names hosting exporter pods.
        """
        pods_kw = KubectlGetPodsKeywords(self.ssh_connection)
        pods_output = pods_kw.get_pods(
            namespace=self._namespace,
            label=self._label,
        )
        nodes = [p.get_node() for p in pods_output.get_pods() if p.get_node()]
        get_logger().log_info(f"Exporter pods on nodes: {nodes}")
        return nodes

    def delete_exporter_pod(self) -> str:
        """Delete the first exporter pod to test recovery.

        Returns:
            str: Name of the deleted pod.

        Raises:
            RuntimeError: If no exporter pods are found.
        """
        pods_kw = KubectlGetPodsKeywords(self.ssh_connection)
        pods_output = pods_kw.get_pods(
            namespace=self._namespace,
            label=self._label,
        )
        pods = pods_output.get_pods()
        if not pods:
            get_logger().log_error(
                f"No exporter pods found with label '{self._label}' "
                f"in namespace '{self._namespace}'"
            )
            raise RuntimeError(
                f"No exporter pods found with label '{self._label}' "
                f"in namespace '{self._namespace}'"
            )

        pod_name = pods[0].get_name()
        get_logger().log_info(f"Deleting exporter pod: {pod_name}")
        cmd = f"kubectl delete pod -n {self._namespace} {pod_name} --grace-period=0"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        return pod_name

    def get_pod_env_value(self, env_name: str) -> str:
        """Get an environment variable value from the first running exporter pod.

        Args:
            env_name (str): Environment variable name (e.g. 'OS_POLLING_INTERVAL').

        Returns:
            str: Environment variable value.

        Raises:
            RuntimeError: If no exporter pods are found.
        """
        pods_kw = KubectlGetPodsKeywords(self.ssh_connection)
        pods_output = pods_kw.get_pods(
            namespace=self._namespace,
            label=self._label,
        )
        pods = pods_output.get_pods()
        if not pods:
            get_logger().log_error(
                f"No exporter pods found with label '{self._label}' "
                f"in namespace '{self._namespace}'"
            )
            raise RuntimeError(
                f"No exporter pods found with label '{self._label}' "
                f"in namespace '{self._namespace}'"
            )

        pod_name = pods[0].get_name()
        jsonpath_kw = KubectlGetPodJsonpathKeywords(self.ssh_connection)
        jsonpath_expr = (
            '{range .spec.containers[*].env[?(@.name=="'
            + env_name
            + '")]}{.value}{end}'
        )
        value = jsonpath_kw.get_pod_jsonpath_value(
            pod_name, jsonpath_expr, self._namespace
        )
        value = value.strip("'").strip()
        get_logger().log_info(f"Pod env {env_name}={value}")
        return value
