from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlLogsKeywords(BaseKeyword):
    """
    Class for 'kubectl logs' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the KubectlLogsKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
        """
        self.ssh_connection = ssh_connection

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

        logs_output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return "\n".join(logs_output) if isinstance(logs_output, list) else str(logs_output)
