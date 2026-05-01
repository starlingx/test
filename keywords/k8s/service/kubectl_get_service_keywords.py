import re
from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.service.object.kubectl_get_service_output import KubectlGetServicesOutput
from keywords.k8s.service.object.kubectl_service_object import KubectlServicesObject


class KubectlGetServiceKeywords(K8sBaseKeyword):
    """
    Keyword class for get service
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_service(self, service_name: str, namespace: str = None) -> KubectlServicesObject:
        """
        Gets the service.

        Args:
            service_name (str): the service name
            namespace (str): the namespace

        Returns:
            KubectlServicesObject: The service object.
        """
        cmd = f"kubectl get service {service_name}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        kubectl_get_service_output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        service_list_output = KubectlGetServicesOutput(kubectl_get_service_output)

        return service_list_output.get_service(service_name)

    def get_services(self, namespace: str = None) -> KubectlServicesObject:
        """
        Gets the services from a namespace.

        Args:
            namespace (str): the namespace

        Returns:
            KubectlServicesObject: The services output object.
        """
        cmd = "kubectl get services"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        kubectl_get_services_output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        services_list_output = KubectlGetServicesOutput(kubectl_get_services_output)
        return services_list_output

    def get_service_node_port(self, service_name: str) -> str:
        """
        Gets the node port for a service.

        Args:
            service_name (str): the service name

        Returns:
            str: The node port value.
        """
        jsonpath = 'jsonpath="{.spec.ports[0].nodePort}"'
        node_port = self.ssh_connection.send(self.k8s_config.export(f"kubectl get service {service_name} -o {jsonpath}"))
        self.validate_success_return_code(self.ssh_connection)
        if len(node_port) > 0:
            return node_port[0]

        return None

    def get_service_endpoint(self, service_name: str, namespace: str = None) -> Optional[str]:
        """Get the endpoint (IP:PORT) of a service via kubectl describe.

        Parses the Endpoints line from ``kubectl describe svc`` output.

        Args:
            service_name (str): Name of the service.
            namespace (str): Namespace of the service. Defaults to None.

        Returns:
            Optional[str]: Endpoint string in IP:PORT format, or None if not found.
        """
        cmd = f"kubectl describe svc {service_name}"
        if namespace:
            cmd = f"{cmd} -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        output_str = "\n".join(output) if isinstance(output, list) else output

        match = re.search(r"Endpoints:\s+([^\s]+)", output_str)
        if match:
            endpoint = match.group(1)
            get_logger().log_info(f"Service {service_name} endpoint: {endpoint}")
            return endpoint

        get_logger().log_info(f"No endpoint found for service {service_name}")
        return None
