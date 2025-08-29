from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config

class KubectlScaleDeploymentsKeywords(BaseKeyword):
    """
    Keyword class for scaling deployments
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def scale_deployment(self, deployment_name: str, replicas: int, namespace: str = None) -> str:
        """
        Scales the given deployment to the specified number of replicas.
        Args:
            deployment_name (str): the deployment name
            replicas (int): number of replicas
            namespace (str): the namespace

        Returns: the output of the scale command
        """
        cmd = f"kubectl scale deployment {deployment_name} --replicas={replicas}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)    
        return output