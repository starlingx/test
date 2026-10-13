from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlRunPodKeywords(K8sBaseKeyword):
    """
    Keywords for running a one-off pod from an image.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def run_pod(self, name: str, image: str, port: int = None, namespace: str = None, restart: str = "Never") -> str:
        """
        Run a one-off pod from an image.

        Args:
            name (str): Name for the pod.
            image (str): Container image to run.
            port (int): Container port to expose on the pod. Optional.
            namespace (str): The namespace. Optional.
            restart (str): The restart policy. Defaults to "Never".

        Returns:
            str: The output of the run command.
        """
        cmd = f"kubectl run {name} --image={image} --restart={restart}"
        if port:
            cmd = f"{cmd} --port={port}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        get_logger().log_info(f"Running pod '{name}' from image '{image}'")
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output
