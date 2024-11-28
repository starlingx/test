from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteDeploymentsKeywords(BaseKeyword):

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def delete_deployment(self, deployment_name: str) -> str:
        """
        Deletes the given deployment
        Args:
            deployment_name (): the deployment name

        Returns: the output

        """
        output = self.ssh_connection.send(export_k8s_config(f"kubectl delete deployment {deployment_name}"))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def cleanup_deployment(self, deployment_name: str) -> int:
        """
        For use in cleanup as it doesn't automatically fail the test
        Args:
            deployment_name (): the deployment name

        Returns: the return code

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl delete deployment {deployment_name}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Deployment {deployment_name} failed to delete")
        return rc
