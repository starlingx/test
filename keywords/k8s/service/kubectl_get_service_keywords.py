from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.service.object.kubectl_get_service_output import KubectlGetServicesOutput
from keywords.k8s.service.object.kubectl_service_object import KubectlServicesObject


class KubectlGetServiceKeywords(BaseKeyword):
    """
    Keyword class for get service
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
        """
        self.ssh_connection = ssh_connection

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
        kubectl_get_service_output = self.ssh_connection.send(export_k8s_config(cmd))
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
        kubectl_get_services_output = self.ssh_connection.send(export_k8s_config(cmd))
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
        node_port = self.ssh_connection.send(export_k8s_config(f"kubectl get service {service_name} -o {jsonpath}"))
        self.validate_success_return_code(self.ssh_connection)
        if len(node_port) > 0:
            return node_port[0]

        return None
