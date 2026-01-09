from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlRolloutRestartKeywords(BaseKeyword):
    """
    Keyword class for kubectl rollout restart operations
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor
        Args:
            ssh_connection (SSHConnection): SSH connection to the target system
        """
        self.ssh_connection = ssh_connection

    def rollout_restart_deployment(self, namespace: str) -> str:
        """
        Restarts all deployments in the specified namespace using rollout restart.

        Args:
            namespace (str): The namespace containing the deployments to restart

        Returns:
            str: The output from the kubectl rollout restart command
        """
        cmd = f"kubectl -n {namespace} rollout restart deploy"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        
        return output
