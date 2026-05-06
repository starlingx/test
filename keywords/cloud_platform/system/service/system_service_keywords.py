from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.service.objects.system_service_output import SystemServiceOutput
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_output import SystemServiceParameterListOutput
from keywords.cloud_platform.system.service.objects.system_service_parameter_output import SystemServiceParameterOutput
from keywords.cloud_platform.system.service.objects.system_service_show_output import SystemServiceShowOutput
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class SystemServiceKeywords(BaseKeyword):
    """Keywords related to the 'system service' commands.

    Args:
        ssh_connection (SSHConnection): SSH connection instance
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_system_service_list(self) -> SystemServiceOutput:
        """
        Gets the system service-list.

        Returns:
            SystemServiceOutput: Object with the list of service.
        """
        command = source_openrc("system service-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_output = SystemServiceOutput(output)
        return system_service_output

    def get_system_service_show(self, service_id: str) -> SystemServiceShowOutput:
        """
        Gets the system service-show.

        Args:
            service_id (str): Service ID

        Returns:
            SystemServiceShowOutput: Service show output object.
        """
        command = source_openrc(f"system service-show {service_id}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_show_output = SystemServiceShowOutput(output)
        return system_service_show_output

    def add_service_parameter(self, service: str, parameter: str, value: str, section: str = "") -> SystemServiceParameterOutput:
        """
        Adds a service parameter.

        Args:
            service (str): The service name
            parameter (str): The parameter to add
            value (str): The value of the parameter
            section (str): Optional section name (e.g., 'sysctl')

        Returns:
            SystemServiceParameterOutput: Output object
        """
        if section:
            command = source_openrc(f"system service-parameter-add {service} {section} {parameter}={value}")
        else:
            command = source_openrc(f"system service-parameter-add {service} {parameter}={value}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_parameter_add_output = SystemServiceParameterOutput(output)
        return system_service_parameter_add_output

    def modify_service_parameter(self, service: str, section: str, parameter: str, value: str) -> SystemServiceParameterOutput:
        """
        Modifies a service parameter.

        Args:
            service (str): The service name (e.g., 'platform')
            section (str): The section name (e.g., 'client')
            parameter (str): The parameter to modify (e.g., 'cli_confirmations')
            value (str): The value of the parameter (e.g., 'enabled')

        Returns:
            SystemServiceParameterOutput: Output object
        """
        command = source_openrc(f'system service-parameter-modify {service} {section} {parameter}="{value}"')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_parameter_modify_output = SystemServiceParameterOutput(output)
        return system_service_parameter_modify_output

    def apply_service_parameters(self, service: str) -> None:
        """
        Applies service parameters.

        Args:
            service (str): The service name (e.g., 'platform', 'kubernetes')
        """
        command = source_openrc(f"system service-parameter-apply {service}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def apply_kubernetes_service_parameters(self) -> None:
        """
        Applies kubernetes service parameters and waits for Kubernetes to restart.

        This method includes validation to ensure Kubernetes stability after parameter changes.
        """
        command = source_openrc("system service-parameter-apply kubernetes")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        # Wait for Kubernetes to restart and stabilize after parameter changes
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_kubernetes_to_restart()

    def get_system_service_parameter_list(self) -> SystemServiceParameterListOutput:
        """
        Gets the system service-parameter-list.

        Returns:
            SystemServiceParameterListOutput: Object with the list of service parameters.
        """
        command = source_openrc("system service-parameter-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemServiceParameterListOutput(output)

    def delete_service_parameter(self, service: str, section: str, parameter: str) -> None:
        """
        Deletes a service parameter by looking up its UUID first.

        Args:
            service (str): The service name (e.g., 'platform')
            section (str): The section name (e.g., 'config')
            parameter (str): The parameter to delete (e.g., 'tls-cipher-suite')
        """
        # Look up the UUID for this parameter
        param_list = self.get_system_service_parameter_list()
        target_uuid = None
        for param in param_list.get_parameters():
            if param.get_service() == service and param.get_section() == section and param.get_name() == parameter:
                target_uuid = param.get_uuid()
                break

        if target_uuid is None:
            raise ValueError(f"Service parameter not found: {service}/{section}/{parameter}")

        command = source_openrc(f"system service-parameter-delete {target_uuid}")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
