from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlCopyToPodKeywords(BaseKeyword):
    """
    Keywords for copying to pods
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def copy_to_pod(self, local_filename: str, namespace: str, pod_name: str, dest_filename):
        """
        Cops the file to the given pod
        Args:
            local_filename (): the path and file name of the local file to be copied
            namespace (): the namespace the pod resides in
            pod_name (): the name of the pod
            dest_filename (): the destination path and file for where the file is being copied

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl cp {local_filename} -n {namespace} {pod_name}:{dest_filename}"))
        self.validate_success_return_code(self.ssh_connection)
