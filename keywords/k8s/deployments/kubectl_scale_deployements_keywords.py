from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlScaleDeploymentsKeywords(K8sBaseKeyword):
    """
    Keyword class for scaling deployments
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def scale_deployment(self, deployment_name: str, replicas: int, namespace: str = None) -> str:
        """Scale the given deployment to the specified number of replicas.

        Args:
            deployment_name (str): The deployment name.
            replicas (int): Number of replicas.
            namespace (str): The namespace. Optional.

        Returns:
            str: The output of the scale command.
        """
        cmd = f"kubectl scale deployment {deployment_name} --replicas={replicas}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output
