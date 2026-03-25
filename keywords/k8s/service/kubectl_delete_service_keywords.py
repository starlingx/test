from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDeleteServiceKeywords(K8sBaseKeyword):
    """
    Delete Service keywords
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def delete_service(self, service_name: str, namespace: str = None) -> str:
        """Delete the given service.

        Args:
            service_name (str): The service name.
            namespace (str): The namespace. Optional.

        Returns:
            str: The output of the delete command.
        """
        cmd = f"kubectl delete service {service_name}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        return output

    def cleanup_service(self, service_name: str) -> str:
        """Delete a service without failing the test on non-zero return code.

        Args:
            service_name (str): The service name.

        Returns:
            str: The return code of the delete command.
        """
        self.ssh_connection.send(self.k8s_config.export(f"kubectl delete service {service_name}"))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"Service {service_name} failed to delete")
        return rc
