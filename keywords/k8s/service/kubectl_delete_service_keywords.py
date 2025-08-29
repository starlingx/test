from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDeleteServiceKeywords(BaseKeyword):
    """
    Delete Service keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def delete_service(self, service_name: str, namespace: str = None) -> str:
        """
        Deletes the given service
        Args:
            service_name (): the service name

        Returns: the output of the cmd

        """
        cmd = f"kubectl delete service {service_name}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def cleanup_service(self, service_name: str) -> str:
        """
        For use in cleanup as it doesn't automatically fail the test
        Args:
            service_name (): the service name

        Returns: the output of the cmd

        """
        self.ssh_connection.send(export_k8s_config(f"kubectl delete service {service_name}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Service {service_name} failed to delete")
        return rc
