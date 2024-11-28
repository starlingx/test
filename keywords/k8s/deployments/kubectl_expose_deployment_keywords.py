from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlExposeDeploymentKeywords(BaseKeyword):
    """
    Class for Expose Deployment Keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def expose_deployment(self, deployment_name: str, type: str, name: str):
        """
        Exposes the deployment
        Args:
            deployment_name (): the deployment name
            type (): the type
            name (): the name

        Returns:

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl expose deployment {deployment_name} --type={type} --name={name}"))
        self.validate_success_return_code(self.ssh_connection)
