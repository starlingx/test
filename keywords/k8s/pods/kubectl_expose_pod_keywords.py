from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlExposePodKeywords(K8sBaseKeyword):
    """
    Keywords for exposing a pod as a service.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def expose_pod(self, pod_name: str, port: int, target_port: int = None, namespace: str = None) -> None:
        """
        Expose a pod as a ClusterIP service.

        Args:
            pod_name (str): The pod to expose. The service takes the same name.
            port (int): The port the service listens on.
            target_port (int): The pod port to forward to. Defaults to port when not given.
            namespace (str): The namespace. Optional.
        """
        cmd = f"kubectl expose pod {pod_name} --port={port}"
        if target_port:
            cmd = f"{cmd} --target-port={target_port}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
