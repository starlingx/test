from typing import List

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.service.objects.system_service_output import SystemServiceOutput
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_object import SystemServiceParameterListObject
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_output import SystemServiceParameterListOutput
from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from keywords.cloud_platform.system.service.objects.system_service_parameter_output import SystemServiceParameterOutput
from keywords.cloud_platform.system.service.objects.system_service_show_output import SystemServiceShowOutput
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class SystemServiceKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system service' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection instance
        """
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

    def get_system_service_parameter_list(self) -> SystemServiceParameterListOutput:
        """
        Gets the system service-parameter-list.

        Returns:
            SystemServiceParameterListOutput: Object with the list of service Parameters.
        """
        command = source_openrc("system service-parameter-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_parameter_output = SystemServiceParameterListOutput(output)
        return system_service_parameter_output

    def get_system_service_parameter_list_by_section(self, section: str) -> SystemServiceParameterListOutput:
        """
        Gets the system service-parameter-list filtered by section.

        Args:
            section (str): Section name to filter by (e.g., 'sysctl')

        Returns:
            SystemServiceParameterListOutput: Object with the filtered list of service Parameters.
        """
        command = source_openrc(f"system service-parameter-list --section {section}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_service_parameter_output = SystemServiceParameterListOutput(output)
        return system_service_parameter_output

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

    def _delete_service_parameter_by_uuid(self, uuid: str) -> str:
        """
        Deletes a service parameter by its UUID.

        Args:
            uuid (str): The UUID of the service parameter to delete.

        Returns:
            str: The command output.
        """
        command = source_openrc(f"system service-parameter-delete {uuid}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return output

    def _find_service_parameter(
        self,
        parameter_list: SystemServiceParameterListOutput,
        service: str,
        section: str,
        name: str,
    ) -> SystemServiceParameterListObject:
        """Find a service parameter by service, section, and name.

        Args:
            parameter_list (SystemServiceParameterListOutput): The full parameter list.
            service (str): The service name.
            section (str): The section name.
            name (str): The parameter name.

        Returns:
            SystemServiceParameterListObject: The matching parameter.

        Raises:
            AssertionError: If the parameter is not found.
        """
        for param in parameter_list.get_parameters():
            if param.service == service and param.section == section and param.name == name:
                return param
        raise AssertionError(f"Service parameter {service} {section} {name} not found")

    def delete_service_parameter(self, service_parameter: SystemServiceParameterObject) -> None:
        """
        Deletes a service parameter.

        Args:
            service_parameter (SystemServiceParameterObject): A SystemServiceParameterObject:
                service (str): The service name (e.g., 'platform')
                section (str): The section name (e.g., 'client')
                name (str): The parameter name (e.g., 'cli_confirmations')
        """
        system_service_parameter_list = self.get_system_service_parameter_list()
        service_parameter_selected = self._find_service_parameter(system_service_parameter_list, service_parameter.service, service_parameter.section, service_parameter.name)
        self._delete_service_parameter_by_uuid(service_parameter_selected.uuid)

    def delete_service_parameters(self, service_parameters: List[SystemServiceParameterListObject]) -> None:
        """
        Deletes multiple service parameters.

        Args:
            service_parameters (List[SystemServiceParameterListObject]): A list of SystemServiceParameterListObjects containing at least:
                service (str): The service name (e.g., 'platform')
                section (str): The section name (e.g., 'client')
                name (str): The parameter name (e.g., 'cli_confirmations')
        """
        system_service_parameter_list = self.get_system_service_parameter_list()
        for service_parameter in service_parameters:
            service_parameter_selected = self._find_service_parameter(system_service_parameter_list, service_parameter.service, service_parameter.section, service_parameter.name)
            self._delete_service_parameter_by_uuid(service_parameter_selected.uuid)

    def cleanup_service_parameters(self, service_parameters: List[SystemServiceParameterListObject]) -> None:
        """
        Cleans up service parameters, ignoring any that's already cleaned.
        """
        system_service_parameter_list = self.get_system_service_parameter_list()
        for service_parameter in service_parameters:
            try:
                service_parameter_selected = self._find_service_parameter(system_service_parameter_list, service_parameter.service, service_parameter.section, service_parameter.name)
            except (AssertionError, Exception):
                continue
            self._delete_service_parameter_by_uuid(service_parameter_selected.uuid)
