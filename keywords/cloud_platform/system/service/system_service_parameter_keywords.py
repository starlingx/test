from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.service.objects.system_service_parameter_list_output import SystemServiceParameterListOutput
from keywords.cloud_platform.system.service.objects.system_service_parameter_output import SystemServiceParameterOutput


class SystemServiceParameterKeywords(BaseKeyword):
    """Keywords related to the 'system service-parameter' commands.

    Args:
        ssh_connection (SSHConnection): SSH connection instance
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def list_service_parameters(
        self,
        service: str = "",
        section: str = "",
    ) -> SystemServiceParameterListOutput:
        """
        Gets the output of 'system service-parameter-list' command

        Args:
            service (str): Filter the list by the service name
            section (str): Filter the list by the section name

        Returns:
            SystemServiceParameterListOutput: The parsed service parameter list output.
        """
        service_str = f"--service {service}" if service else ""
        section_str = f"--section {section}" if section else ""
        command = source_openrc(f"system service-parameter-list {service_str} {section_str}")
        output_str = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemServiceParameterListOutput(output_str)

    def list_service_parameters_with_error(
        self,
        service: str = "",
        section: str = "",
    ) -> str:
        """
        Runs 'system service-parameter-list' expecting rejection.

        Args:
            service (str): Filter the list by the service name
            section (str): Filter the list by the section name

        Returns:
            str: The error output from the rejected command.
        """
        service_str = f"--service {service}" if service else ""
        section_str = f"--section {section}" if section else ""
        command = source_openrc(f"system service-parameter-list {service_str} {section_str}")
        error_output_str = self.ssh_connection.send(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return error_output_str

    def show_service_parameter(
        self,
        uuid: str,
    ) -> SystemServiceParameterOutput:
        """Show a service parameter by UUID.

        Args:
            uuid (str): The service parameter 'uuid'

        Returns:
            SystemServiceParameterOutput: The parsed service parameter output.
        """
        command = source_openrc(f"system service-parameter-show {uuid}")
        output_str = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemServiceParameterOutput(output_str)

    def show_service_parameter_with_error(
        self,
        uuid: str,
    ) -> str:
        """
        Runs 'system service-parameter-show' expecting rejection.

        Args:
            uuid (str): The service parameter 'uuid'

        Returns:
            str: The error output from the rejected command.
        """
        command = source_openrc(f"system service-parameter-show {uuid}")
        error_output_str = self.ssh_connection.send(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return error_output_str

    def add_service_parameter(
        self,
        service: str,
        section: str,
        parameter_name: str,
        parameter_value: str,
    ) -> SystemServiceParameterOutput:
        """
        Adds a single service parameter.

        Args:
            service (str): The service name
            section (str): The section name
            parameter_name (str): The parameter to add
            parameter_value (str): The value of the parameter

        Returns:
            SystemServiceParameterOutput: The parsed service parameter output.
        """
        command = source_openrc(f"system service-parameter-add {service} {section} " f'{parameter_name}="{parameter_value}"')
        output_str = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemServiceParameterOutput(output_str)

    def add_service_parameter_with_error(
        self,
        service: str,
        section: str,
        parameter_name: str,
        parameter_value: str,
    ) -> str:
        """
        Runs 'system service-parameter-add' expecting rejection.

        Args:
            service (str): The service name
            section (str): The section name
            parameter_name (str): The parameter to add
            parameter_value (str): The value of the parameter

        Returns:
            str: The error output from the rejected command.
        """
        command = source_openrc(f"system service-parameter-add {service} {section} " f'{parameter_name}="{parameter_value}"')
        error_output_str = self.ssh_connection.send(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return error_output_str

    def modify_service_parameter(
        self,
        service: str,
        section: str,
        parameter_name: str,
        parameter_value: str,
    ) -> SystemServiceParameterOutput:
        """
        Modifies a service parameter.

        Args:
            service (str): The service name (e.g., 'platform')
            section (str): The section name (e.g., 'client')
            parameter_name (str): The parameter name (e.g., 'cli_confirmations')
            parameter_value (str): The value of the parameter (e.g., 'enabled')

        Returns:
            SystemServiceParameterOutput: The parsed service parameter output.
        """
        command = source_openrc(f"system service-parameter-modify {service} {section}" f' {parameter_name}="{parameter_value}"')
        output_str = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemServiceParameterOutput(output_str)

    def modify_service_parameter_with_error(
        self,
        service: str,
        section: str,
        parameter_name: str,
        parameter_value: str,
    ) -> str:
        """
        Runs 'system service-parameter-modify' expecting rejection.

        Args:
            service (str): The service name (e.g., 'platform')
            section (str): The section name (e.g., 'client')
            parameter_name (str): The parameter name (e.g., 'cli_confirmations')
            parameter_value (str): The value of the parameter (e.g., 'enabled')

        Returns:
            str: The error output from the rejected command.
        """
        command = source_openrc(f"system service-parameter-modify {service} {section}" f' {parameter_name}="{parameter_value}"')
        error_output_str = self.ssh_connection.send(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return error_output_str

    def add_multiple_service_parameters(
        self,
        service: str,
        section: str,
        parameters_str: str,
    ) -> SystemServiceParameterOutput:
        """Adds multiple service parameters at once.

        The parameters belong to the same service + section.

        Args:
            service (str): The service name
            section (str): The section name
            parameters_str (str): The parameters and values to add
                                  e.g '<name>=<value> <name2>=<value2> ...'

        Returns:
            SystemServiceParameterOutput: The parsed service parameter output.
        """
        command = source_openrc(f"system service-parameter-add {service} {section} " f"{parameters_str}")
        output_str = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemServiceParameterOutput(output_str)

    def add_multiple_service_parameters_with_error(
        self,
        service: str,
        section: str,
        parameters_str: str,
    ) -> str:
        """
        Runs 'system service-parameter-add' (multiple) expecting rejection.

        Args:
            service (str): The service name
            section (str): The section name
            parameters_str (str): The parameters and values to add
                                  e.g '<name>=<value> <name2>=<value2> ...'

        Returns:
            str: The error output from the rejected command.
        """
        command = source_openrc(f"system service-parameter-add {service} {section} " f"{parameters_str}")
        error_output_str = self.ssh_connection.send(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return error_output_str

    def modify_multiple_service_parameters(
        self,
        service: str,
        section: str,
        parameters_str: str,
    ) -> SystemServiceParameterOutput:
        """Modifies multiple service parameters at once.

        The parameters belong to the same service + section.

        Args:
            service (str): The service name
            section (str): The section name
            parameters_str (str): The parameters and values to add
                                  e.g '<name>=<value> <name2>=<value2> ...'

        Returns:
            SystemServiceParameterOutput: The parsed service parameter output.
        """
        command = source_openrc(f"system service-parameter-modify {service} {section} " f"{parameters_str}")
        output_str = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return SystemServiceParameterOutput(output_str)

    def modify_multiple_service_parameters_with_error(
        self,
        service: str,
        section: str,
        parameters_str: str,
    ) -> str:
        """
        Runs 'system service-parameter-modify' (multiple) expecting rejection.

        Args:
            service (str): The service name
            section (str): The section name
            parameters_str (str): The parameters and values to add
                                  e.g '<name>=<value> <name2>=<value2> ...'

        Returns:
            str: The error output from the rejected command.
        """
        command = source_openrc(f"system service-parameter-modify {service} {section} " f"{parameters_str}")
        error_output_str = self.ssh_connection.send(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return error_output_str

    def delete_service_parameter(
        self,
        uuid: str,
    ) -> str:
        """
        Deletes a service parameter.

        Args:
            uuid (str): The uuid of the service parameter

        Returns:
            str: The command output string
        """
        command = source_openrc(f"system service-parameter-delete {uuid}")
        output_str = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return output_str

    def delete_service_parameter_with_error(
        self,
        uuid: str,
    ) -> str:
        """
        Runs 'system service-parameter-delete' expecting rejection.

        Args:
            uuid (str): The uuid of the service parameter

        Returns:
            str: The command output string
        """
        command = source_openrc(f"system service-parameter-delete {uuid}")
        error_output_str = self.ssh_connection.send(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return error_output_str

    def apply_service_parameters(
        self,
        service: str,
    ) -> str:
        """
        Applies service parameters.

        Args:
            service (str): The service name (e.g., 'platform', 'kubernetes')

        Returns:
            str: The command output string
        """
        command = source_openrc(f"system service-parameter-apply {service}")
        output_str = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        return output_str

    def apply_service_parameters_with_error(
        self,
        service: str,
    ) -> str:
        """
        Runs 'system service-parameter-apply' expecting rejection.

        Args:
            service (str): The service name (e.g., 'platform', 'kubernetes')

        Returns:
            str: The command output string
        """
        command = source_openrc(f"system service-parameter-apply {service}")
        error_output_str = self.ssh_connection.send(command)
        self.validate_cmd_rejection_return_code(self.ssh_connection)
        return error_output_str
