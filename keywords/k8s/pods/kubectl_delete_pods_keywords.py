from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeletePodsKeywords(BaseKeyword):
    """
    Keywords for delete pods
    """

    def __init__(self, ssh_connection: object):
        """Constructor.

        Args:
            ssh_connection (object): SSH connection object.
        """
        self.ssh_connection = ssh_connection

    def delete_pod(self, pod_name: str, namespace: str = "default") -> str:
        """Deletes the pod.

        Args:
            pod_name (str): the pod name
            namespace (str): the namespace. Defaults to "default"

        Returns:
            str: the output
        """
        cmd = f"kubectl delete pod {pod_name} -n {namespace}"

        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def cleanup_pod(self, pod_name: str, namespace: str = None) -> int:
        """For use in cleanup as it doesn't automatically fail the test.

        Deletes the pod
        Args:
            pod_name (str): the pod
            namespace (str): the namespace

        Returns:
            int: the output
        """
        arg_namespace = ""
        if namespace:
            arg_namespace = f"-n {namespace}"

        self.ssh_connection.send(export_k8s_config(f"kubectl {arg_namespace} delete pod {pod_name}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Pod {pod_name} failed to delete")
        return rc
