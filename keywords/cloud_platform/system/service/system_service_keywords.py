from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.service.objects.system_service_output import SystemServiceOutput
from keywords.cloud_platform.system.service.objects.system_service_show_output import SystemServiceShowOutput
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from time import sleep


class SystemServiceKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system service' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_service_list(self) -> SystemServiceOutput:
        """
        Gets the system service-list

        Args:

        Returns:
            SystemServiceOutput object with the list of service.

        """
        command = source_openrc(f'system service-list')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_output = SystemServiceOutput(output)
        return system_service_output

    def get_system_service_show(self, service_id) -> SystemServiceShowOutput:
        """
        Gets the system service-show

        Args:
            service_id: service_id

        Returns:
            SystemServiceShowOutput object.

        """
        command = source_openrc(f'system service-show {service_id}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_show_output = SystemServiceShowOutput(output)
        return system_service_show_output
    

    def add_service_parameter(self, service: str, parameter: str, value: str):
        """
        Adds a service parameter.

        Args:
            service (str): The service name.
            parameter (str): The parameter to add.
            value (str): The value of the parameter.
        """
        command = source_openrc(f'system service-parameter-add {service} {parameter}={value}')
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def apply_kubernetes_service_parameters(self):
        """
        Applies kubernetes service parameters and waits for it to restart.
        """
        command = source_openrc(f'system service-parameter-apply kubernetes')
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_kubernetes_to_restart()
