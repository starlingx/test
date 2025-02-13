from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_ptp_parameter_output import SystemPTPParameterOutput
from keywords.cloud_platform.system.ptp.objects.system_ptp_parameter_list_output import SystemPTPParameterListOutput

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

    def system_ptp_parameter_modify(self,uuid: str, new_value: str) -> SystemPTPParameterOutput :
        """
        Modify a PTP parameter
        
        Args:
            uuid : uuid for ptp parameter name
            new_value: new value for PTP parameter

        Returns:
        """
        cmd = f"system ptp-parameter-modify {uuid} {new_value}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_parameter_modify_output = SystemPTPParameterOutput(output)

        return system_ptp_parameter_modify_output

    def get_system_ptp_parameter_show(self,uuid: str) -> SystemPTPParameterOutput :
        """
        show an PTP parameter attributes.
        
        Args:
            uuid : uuid for ptp parameter name

        Returns:
        """
        cmd = f"system ptp-parameter-show {uuid}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_parameter_show_output = SystemPTPParameterOutput(output)
        
        return system_ptp_parameter_show_output
    
    def get_system_ptp_parameter_list(self) -> SystemPTPParameterListOutput :
        """
        List all PTP parameters

        Returns:
        """
        command = source_openrc("system ptp-parameter-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_parameter_list_output = SystemPTPParameterListOutput(output)

        return system_ptp_parameter_list_output


