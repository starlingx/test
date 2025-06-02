from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_ptp_parameter_list_output import SystemPTPParameterListOutput
from keywords.cloud_platform.system.ptp.objects.system_ptp_parameter_output import SystemPTPParameterOutput


class SystemPTPParameterKeywords(BaseKeyword):
    """
    Provides methods to interact with the system ptp-parameter
    using given SSH connection.

    Attributes:
        ssh_connection: An interface of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SystemPTPParameterKeywords with an SSH connection.

        Args:
            ssh_connection: An interface of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def system_ptp_parameter_modify(self, uuid: str, new_value: str) -> SystemPTPParameterOutput:
        """
        Modify a PTP parameter

        Args:
            uuid (str): uuid for ptp parameter name
            new_value (str): new value for PTP parameter

        Returns:
            SystemPTPParameterOutput: Output of the command
        """
        cmd = f"system ptp-parameter-modify {uuid} {new_value}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_parameter_modify_output = SystemPTPParameterOutput(output)

        return system_ptp_parameter_modify_output

    def system_ptp_parameter_modify_with_error(self, uuid: str, new_value: str) -> str:
        """
        Modify a PTP parameter for errors.

        Args:
            uuid (str): uuid for ptp parameter name
            new_value (str): new value for PTP parameter

        Returns:
            str: Output of the command
        """
        cmd = f"system ptp-parameter-modify {uuid} {new_value}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def get_system_ptp_parameter_show(self, uuid: str) -> SystemPTPParameterOutput:
        """
        show an PTP parameter attributes.

        Args:
            uuid (str): uuid for ptp parameter name

        Returns:
            SystemPTPParameterOutput: system ptp parameter output
        """
        cmd = f"system ptp-parameter-show {uuid}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_parameter_show_output = SystemPTPParameterOutput(output)

        return system_ptp_parameter_show_output

    def get_system_ptp_parameter_list(self) -> SystemPTPParameterListOutput:
        """
        List all PTP parameters

        Returns:
            SystemPTPParameterListOutput: system ptp parameter list output
        """
        command = source_openrc("system ptp-parameter-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_parameter_list_output = SystemPTPParameterListOutput(output)

        return system_ptp_parameter_list_output
