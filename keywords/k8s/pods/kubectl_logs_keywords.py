from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlLogsKeywords(K8sBaseKeyword):
    """
    Class for 'kubectl logs' keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """
        Initialize the KubectlLogsKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_logs(self, pod_name: str, namespace: str = None, tail: int = None) -> str:
        """
        Gets the logs from a pod.

        Args:
            pod_name (str): The name of the pod.
            namespace (str, optional): The namespace of the pod.
            tail (int, optional): Number of lines to show from the end of the logs.

        Returns:
            str: The logs from the pod.
        """
        cmd = f"kubectl logs {pod_name}"

        if namespace:
            cmd += f" -n {namespace}"

        if tail:
            cmd += f" --tail={tail}"

        logs_output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return "\n".join(logs_output) if isinstance(logs_output, list) else str(logs_output)
