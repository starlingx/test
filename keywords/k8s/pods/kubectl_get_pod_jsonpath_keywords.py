import re

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_not_none
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter


class KubectlGetPodJsonpathKeywords(BaseKeyword):
    """Class for getting pod values using kubectl jsonpath output."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        self.ssh_connection = ssh_connection
        self.k8s_config = K8sConfigExporter(kubeconfig_path)

    def get_pod_jsonpath_value(self, pod_name: str, jsonpath: str, namespace: str = None) -> str:
        """Get a value from a pod using kubectl jsonpath.

        Args:
            pod_name: Name of the pod.
            jsonpath: JSONPath expression.
            namespace: Namespace of the pod.

        Returns:
            str: The jsonpath output.
        """
        ns_arg = f"-n {namespace}" if namespace else ""
        cmd = f"kubectl get pod/{pod_name} {ns_arg} -o jsonpath='{jsonpath}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return "\n".join(output) if isinstance(output, list) else str(output)

    def get_container_id(self, pod_name: str, namespace: str = None) -> str:
        """Get the containerd container ID from a pod.

        Args:
            pod_name: Name of the pod.
            namespace: Namespace of the pod.

        Returns:
            str: The container UUID.

        Raises:
            KeywordException: If container ID cannot be extracted.
        """
        jsonpath = "{..status.containerStatuses[].containerID}"
        output = self.get_pod_jsonpath_value(pod_name, jsonpath, namespace)
        match = re.search(r'containerd://(.*)', output)
        validate_not_none(match, f"Cannot find containerd UUID in {output}")
        return match.group(1).strip()
