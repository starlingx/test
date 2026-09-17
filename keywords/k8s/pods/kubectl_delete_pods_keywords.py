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

    def cleanup_pod(self, pod_name: str, namespace: str = None, force: bool = False, grace_period: int = None) -> int:
        """For use in cleanup as it doesn't automatically fail the test.

        Deletes the pod. By default performs a graceful delete; set force=True
        (optionally with grace_period=0) to force-delete a pod that is stuck
        Terminating so it releases its resources (e.g. an attached volume)
        immediately.

        Args:
            pod_name (str): the pod
            namespace (str): the namespace
            force (bool): if True, add --force to the delete command
            grace_period (int): if set, add --grace-period=<value> (e.g. 0)

        Returns:
            int: the output
        """
        arg_namespace = ""
        if namespace:
            arg_namespace = f"-n {namespace}"

        force_arg = "--force" if force else ""
        grace_arg = f"--grace-period={grace_period}" if grace_period is not None else ""

        cmd = f"kubectl {arg_namespace} delete pod {pod_name} {force_arg} {grace_arg}".split()
        self.ssh_connection.send(self.k8s_config.export(" ".join(cmd)))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Pod {pod_name} failed to delete")
        return rc

    def delete_from_yaml(self, yaml_file: str, namespace: str = None, ignore_not_found: bool = True) -> None:
        """Deletes resources defined in a YAML file.

        Args:
            yaml_file (str): Path to the YAML file on the controller.
            namespace (str): Optional namespace override.
            ignore_not_found (bool): If True, adds --ignore-not-found flag.
        """
        ns_arg = f"-n {namespace}" if namespace else ""
        ignore_arg = "--ignore-not-found" if ignore_not_found else ""
        cmd = f"kubectl delete -f {yaml_file} {ns_arg} {ignore_arg}".strip()
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
