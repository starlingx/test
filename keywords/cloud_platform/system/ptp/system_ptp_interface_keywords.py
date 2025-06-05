from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_ptp_interface_list_output import SystemPTPInterfaceListOutput
from keywords.cloud_platform.system.ptp.objects.system_ptp_interface_output import SystemPTPInterfaceOutput


class SystemPTPInterfaceKeywords(BaseKeyword):
    """
    Provides methods to interact with the system ptp-interface
    using given SSH connection.

    Attributes:
        ssh_connection: An interface of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SystemPTPInterfaceKeywords with an SSH connection.

        Args:
            ssh_connection: An interface of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def system_ptp_interface_add(self, name: str, ptp_instance_name: str) -> SystemPTPInterfaceOutput:
        """
        Add a PTP interface

        Args:
            name (str): name of interface
            ptp_instance_name (str): ptp instance name

        Returns:
            SystemPTPInterfaceOutput: Output of the command
        """
        cmd = f"system ptp-interface-add {name} {ptp_instance_name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_interface_add_output = SystemPTPInterfaceOutput(output)

        return system_ptp_interface_add_output

    def system_ptp_interface_add_with_error(self, name: str, ptp_instance_name: str) -> str:
        """
        Add a PTP interface for errors.

        Args:
            name (str): name of interface
            ptp_instance_name (str): ptp instance name

        Returns:
            str: Output of the command
        """
        cmd = f"system ptp-interface-add {name} {ptp_instance_name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def system_ptp_interface_delete(self, name: str) -> str:
        """
        Delete an interface

        Args:
            name (str): name or UUID of interface

        Returns:
            str: Success message
        """
        cmd = f"system ptp-interface-delete {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)

        # output is a List of 1 string. "['Deleted PTP interface: xxxx-xxxx-xxx\n']"
        if output and len(output) > 0:
            return output[0].strip()
        else:
            raise Exception("Output is expected to be a List with one element.")

    def system_ptp_interface_delete_with_error(self, name: str) -> str:
        """
        Delete an interface for errors.

        Args:
            name (str): name or UUID of interface

        Returns:
            str: Command output
        """
        cmd = f"system ptp-interface-delete {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def get_system_ptp_interface_show(self, name: str) -> SystemPTPInterfaceOutput:
        """
        Show PTP interface attributes.

        Args:
            name (str): name or UUID of interface

        Returns:
            SystemPTPInterfaceOutput: Output of the command
        """
        cmd = f"system ptp-interface-show {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_interface_show_output = SystemPTPInterfaceOutput(output)

        return system_ptp_interface_show_output

    def get_system_ptp_interface_show_with_error(self, name: str) -> str:
        """
        Show PTP interface attributes for errors.

        Args:
            name (str): name or UUID of interface

        Returns:
            str: Output of the command
        """
        cmd = f"system ptp-interface-show {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def get_system_ptp_interface_list(self) -> SystemPTPInterfaceListOutput:
        """
        List all PTP interfaces

        Returns:
            SystemPTPInterfaceListOutput: System PTP Interface List Output
        """
        command = source_openrc("system ptp-interface-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_interface_list_output = SystemPTPInterfaceListOutput(output)

        return system_ptp_interface_list_output

    def system_ptp_interface_parameter_add(self, name: str, parameters: str) -> SystemPTPInterfaceOutput:
        """
        Add interface level parameters

        Args:
            name (str): name or uuid of interface
            parameters (str): parameters can be applied to the interface
                Ex : system ptp-interface-parameter-add ptpinterface masterOnly=1
                    system ptp-interface-parameter-add ptpinterface masterOnly=0 domainNumber=0

        Returns:
            SystemPTPInterfaceOutput: Output of the command
        """
        cmd = f"system ptp-interface-parameter-add {name} {parameters}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_interface_parameter_add_output = SystemPTPInterfaceOutput(output)

        return system_ptp_interface_parameter_add_output

    def system_ptp_interface_parameter_add_with_error(self, name: str, parameters: str) -> str:
        """
        Add interface level parameters for errors.

        Args:
            name (str): name or uuid of interface
            parameters (str): parameters can be applied to the interface
                Ex : system ptp-interface-parameter-add ptpinterface masterOnly=1
                    system ptp-interface-parameter-add ptpinterface masterOnly=0 domainNumber=0

        Returns:
            str: Output of the command
        """
        cmd = f"system ptp-interface-parameter-add {name} {parameters}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def system_ptp_interface_parameter_delete(self, name: str, parameters: str) -> SystemPTPInterfaceOutput:
        """
        Delete interface level parameters

        Args:
            name (str): name or uuid of interface
            parameters (str): parameters can be delete from the interface
                Ex : system ptp-interface-parameter-delete ptpinterface masterOnly=1
                    system ptp-interface-parameter-delete ptpinterface masterOnly=0 domainNumber=0

        Returns:
            SystemPTPInterfaceOutput: Output of the command
        """
        cmd = f"system ptp-interface-parameter-delete {name} {parameters}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_ptp_interface_parameter_delete_output = SystemPTPInterfaceOutput(output)

        return system_ptp_interface_parameter_delete_output

    def system_ptp_interface_parameter_delete_with_error(self, name: str, parameters: str) -> str:
        """
        Delete interface level parameters for errors.

        Args:
            name (str): name or uuid of interface
            parameters (str): parameters can be delete from the interface
                Ex : system ptp-interface-parameter-delete ptpinterface masterOnly=1
                    system ptp-interface-parameter-delete ptpinterface masterOnly=0 domainNumber=0

        Returns:
            str: Output of the command
        """
        cmd = f"system ptp-interface-parameter-delete {name} {parameters}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)
