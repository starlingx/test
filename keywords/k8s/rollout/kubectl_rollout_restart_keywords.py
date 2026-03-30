from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlRolloutRestartKeywords(K8sBaseKeyword):
    """
    Keyword class for kubectl rollout restart operations
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def rollout_restart_deployment(self, namespace: str) -> str:
        """Restart all deployments in the specified namespace using rollout restart.

        Args:
            namespace (str): The namespace containing the deployments to restart

        Returns:
            str: The output from the kubectl rollout restart command
        """
        cmd = f"kubectl -n {namespace} rollout restart deploy"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output
