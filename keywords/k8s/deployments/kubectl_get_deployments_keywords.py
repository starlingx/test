from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.deployments.object.kubectl_get_deployments_output import KubectlGetDeploymentOutput
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlGetDeploymentsKeywords(BaseKeyword):
    """
    Class for Expose Deployment Keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
        """
        self.ssh_connection = ssh_connection

    def get_deployment(self, deployment_name: str, namespace: str = None) -> KubectlGetDeploymentOutput:
        """
        Get the deployments from the specified name.

        Args:
            deployment_name (str): the deployment name
            namespace (str): the namespace

        Returns:
            KubectlGetDeploymentOutput: The deployment output object.
        """
        cmd = f"kubectl get deployment {deployment_name}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        kubectl_get_deployments_output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        deployments_list_output = KubectlGetDeploymentOutput(kubectl_get_deployments_output)

        return deployments_list_output

    def get_deployments(self, namespace: str = None) -> KubectlGetDeploymentOutput:
        """
        Get the deployments from the specified namespace, or all namespaces if not specified.

        Args:
            namespace (str): the namespace

        Returns:
            KubectlGetDeploymentOutput: The deployment output object.
        """
        cmd = "kubectl get deployment"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        kubectl_get_deployments_output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        deployments_list_output = KubectlGetDeploymentOutput(kubectl_get_deployments_output)

        return deployments_list_output
