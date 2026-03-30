from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteHelmReleaseKeywords(K8sBaseKeyword):
    """
    Class for 'kubectl delete hr' keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_helm_release(self, namespace: str, helm_name: str) -> str:
        """
        Deletes the helm release for a given namespace.

        Args:
            namespace (str): the namespace
            helm_name (str): the helm release name

        Returns:
             str: the output of the command

        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl delete hr -n {namespace} {helm_name}"))
        self.validate_success_return_code(self.ssh_connection)

        return output
