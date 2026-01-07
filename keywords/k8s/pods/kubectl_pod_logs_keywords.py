from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlPodLogsKeywords(BaseKeyword):
    """
    Class for 'kubectl logs' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the KubectlPodLogsKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
        """
        self.ssh_connection = ssh_connection

    def get_pod_logs(self, pod_name: str, namespace: str = "default", tail_lines: int = -1, grep_pattern: str = None, since: str = None) -> list:
        """Get logs from a specific pod.

        Args:
            pod_name (str): Name of the pod to get logs from.
            namespace (str): Kubernetes namespace. Defaults to "default".
            tail_lines (int): Number of recent log lines to retrieve. Defaults to -1 (all logs).
            grep_pattern (str): Pattern to filter logs. Optional.
            since (str): Only return logs newer than a relative duration like 5s, 2m, or 3h. Optional.

        Returns:
            list: Log output lines.
        """
        cmd = f"kubectl logs {pod_name} -n {namespace}"

        if since:
            cmd += f" --since={since}"
        elif tail_lines != -1:
            cmd += f" --tail={tail_lines}"

        if grep_pattern:
            cmd += f" | grep -i '{grep_pattern}' || echo 'No matches found for pattern: {grep_pattern}'"

        return self.ssh_connection.send(export_k8s_config(cmd))
