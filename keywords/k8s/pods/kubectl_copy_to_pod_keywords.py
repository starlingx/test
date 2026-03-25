from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlCopyToPodKeywords(K8sBaseKeyword):
    """
    Keywords for copying to pods
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """
        Initialize the KubectlCopyToPodKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def copy_to_pod(self, local_filename: str, namespace: str, pod_name: str, dest_filename: str):
        """Copies the file to the given pod.

        Args:
            local_filename (str): the path and file name of the local file to be copied
            namespace (str): the namespace the pod resides in
            pod_name (str): the name of the pod
            dest_filename (str): the destination path and file for where the file is being copied
        """
        cmd = f"kubectl cp {local_filename} -n {namespace} {pod_name}:{dest_filename}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
