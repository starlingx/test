from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlExposeDeploymentKeywords(K8sBaseKeyword):
    """
    Class for Expose Deployment Keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def expose_deployment(self, deployment_name: str, type: str, name: str) -> None:
        """Expose the deployment as a service.

        Args:
            deployment_name (str): The deployment name.
            type (str): The service type.
            name (str): The service name.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl expose deployment {deployment_name} --type={type} --name={name}"))
        self.validate_success_return_code(self.ssh_connection)
