from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.deployments.object.kubectl_get_deployments_output import KubectlGetDeploymentOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetDeploymentsKeywords(K8sBaseKeyword):
    """
    Class for Expose Deployment Keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

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
        kubectl_get_deployments_output = self.ssh_connection.send(self.k8s_config.export(cmd))
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
        kubectl_get_deployments_output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        deployments_list_output = KubectlGetDeploymentOutput(kubectl_get_deployments_output)

        return deployments_list_output
