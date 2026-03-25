from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeletePodsKeywords(K8sBaseKeyword):
    """
    Keywords for delete pods
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_pod(self, pod_name: str, namespace: str = "default") -> str:
        """Deletes the pod.

        Args:
            pod_name (str): the pod name
            namespace (str): the namespace. Defaults to "default"

        Returns:
            str: the output
        """
        cmd = f"kubectl delete pod {pod_name} -n {namespace}"

        output = self.ssh_connection.send(self.k8s_config.export(cmd))
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

        self.ssh_connection.send(self.k8s_config.export(f"kubectl {arg_namespace} delete pod {pod_name}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Pod {pod_name} failed to delete")
        return rc
