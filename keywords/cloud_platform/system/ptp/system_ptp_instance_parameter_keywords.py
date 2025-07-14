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

    def system_ptp_instance_parameter_add(self, instance_name: str, parameter: str) -> SystemPTPInstanceOutput:
        """
        Add a parameter to a PTP instance.

        Args:
            instance_name (str): Name or UUID of the PTP instance
            parameter (str): Parameter key=value pair to add

        Returns:
            SystemPTPInstanceOutput: Output of the command
        """
        cmd = f"system ptp-instance-parameter-add {instance_name} {parameter}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_instance_parameter_add_output = SystemPTPInstanceOutput(output)

        return system_ptp_instance_parameter_add_output

    def system_ptp_instance_parameter_delete(self, instance_name: str, parameter: str) -> SystemPTPInstanceOutput:
        """
        Delete a parameter from a PTP instance.

        Args:
            instance_name (str): Name or UUID of the PTP instance
            parameter (str): Parameter key to delete

        Returns:
            SystemPTPInstanceOutput: Output of the command
        """
        cmd = f"system ptp-instance-parameter-delete {instance_name} {parameter}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_instance_parameter_delete_output = SystemPTPInstanceOutput(output)

        return system_ptp_instance_parameter_delete_output

    def system_ptp_instance_parameter_add_with_error(self, instance: str, parameter: str) -> str:
        """
        Add a parameter to a PTP instance for errors.

        Args:
            instance (str): name or UUID of instance
            parameter (str): parameter keypair to add

        Returns:
            str: Command output
        """
        cmd = f"system ptp-instance-parameter-add {instance} {parameter}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def system_ptp_instance_parameter_delete_with_error(self, instance: str, parameter: str) -> str:
        """
        Delete a parameter from a PTP instance for errors.

        Args:
            instance (str): name or UUID of instance
            parameter (str): name or UUID of parameter

        Returns:
            str: Command output
        """
        cmd = f"system ptp-instance-parameter-delete {instance} {parameter}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)
