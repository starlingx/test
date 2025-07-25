from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_ptp_instance_list_output import SystemPTPInstanceListOutput
from keywords.cloud_platform.system.ptp.objects.system_ptp_instance_output import SystemPTPInstanceOutput


class SystemPTPInstanceKeywords(BaseKeyword):
    """
    Provides methods to interact with the system ptp-instance
    using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SystemPTPInstanceKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def system_ptp_instance_add(self, name: str, service: str) -> SystemPTPInstanceOutput:
        """
        Create an instance by providing a name and type

        Args:
            name (str): name of instance
            service (str): type of instance

        Returns:
            SystemPTPInstanceOutput: Output of the command
        """
        cmd = f"system ptp-instance-add {name} {service}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_instance_add_output = SystemPTPInstanceOutput(output)

        return system_ptp_instance_add_output

    def system_ptp_instance_add_with_error(self, name: str, service: str) -> str:
        """
        Create an instance by providing a name and type for errors.

        Args:
            name (str): name of instance
            service (str): type of instance

        Returns:
            str: Output of the command
        """
        cmd = f"system ptp-instance-add {name} {service}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def system_ptp_instance_delete(self, name: str) -> str:
        """
        Delete an instance

        Args:
            name (str): name or UUID of instance

        Returns:
            str: Success message
        """
        cmd = f"system ptp-instance-delete {name}"
        command = source_openrc(cmd)
        self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)

    def system_ptp_instance_delete_with_error(self, name: str) -> str:
        """
        Delete an instance for errors.

        Args:
            name (str): name or UUID of instance

        Returns:
            str: Command output
        """
        cmd = f"system ptp-instance-delete {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def get_system_ptp_instance_show(self, name: str) -> SystemPTPInstanceOutput:
        """
        Show PTP instance attributes.

        Args:
            name (str): name or UUID of instance

        Returns:
            SystemPTPInstanceOutput: Output of the command
        """
        cmd = f"system ptp-instance-show {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_instance_show_output = SystemPTPInstanceOutput(output)

        return system_ptp_instance_show_output

    def get_system_ptp_instance_show_with_error(self, name: str) -> str:
        """
        Show PTP instance attributes for errors.

        Args:
            name (str): name or UUID of instance

        Returns:
            str: Output of the command
        """
        cmd = f"system ptp-instance-show {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def get_system_ptp_instance_list(self) -> SystemPTPInstanceListOutput:
        """
        List all PTP instances

        Returns:
            SystemPTPInstanceListOutput: system ptp instance list output
        """
        command = source_openrc("system ptp-instance-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_instance_list_output = SystemPTPInstanceListOutput(output)

        return system_ptp_instance_list_output

    def system_ptp_instance_apply(self) -> str:
        """
        Apply the PTP Instance config

        Returns:
            str: Command output
        """
        command = source_openrc("system ptp-instance-apply")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        # output is a List of 1 string. "['Applying the PTP Instance configuration\n']"
        if output and len(output) > 0:
            return output[0].strip()
        else:
            raise "Output is expected to be a List with one element."
