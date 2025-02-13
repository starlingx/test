from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_ptp_instance_output import SystemPTPInstanceOutput

class SystemPTPInstanceParameterKeywords(BaseKeyword):
    """
    Provides methods to interact with the system ptp-instance-parameter
    using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SystemPTPInstanceParameterKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def system_ptp_instance_parameter_add(self,name: str, parameters: str) -> SystemPTPInstanceOutput :
        """
        Add parameter to instance
        
        Args:
            name : name or UUID of instance
            parameters: parameters can be applied to the service of a instance
                Ex : system ptp-instance-parameter-add ptp1 masterOnly=0
                    system ptp-instance-parameter-add ptp1 masterOnly=0 domainNumber=0

        Returns:
        """
        cmd = f"system ptp-instance-parameter-add {name} {parameters}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_instance_parameter_add_output = SystemPTPInstanceOutput(output)

        return system_ptp_instance_parameter_add_output

    def system_ptp_instance_parameter_delete(self,name: str, parameters: str) -> SystemPTPInstanceOutput :
        """
        Delete parameter to instance
        
        Args:
            name : name or UUID of instance
            parameters: parameters can be delete from the service of a instance
                Ex : system ptp-instance-parameter-delete ptp1 masterOnly=0
                    system ptp-instance-parameter-delete ptp1 masterOnly=0 domainNumber=0

        Returns:
        """
        cmd = f"system ptp-instance-parameter-delete {name} {parameters}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_instance_parameter_delete_output = SystemPTPInstanceOutput(output)

        return system_ptp_instance_parameter_delete_output