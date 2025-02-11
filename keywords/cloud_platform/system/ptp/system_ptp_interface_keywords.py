from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_ptp_interface_output import SystemPTPInterfaceOutput
from keywords.cloud_platform.system.ptp.objects.system_ptp_interface_list_output import SystemPTPInterfaceListOutput

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

    def system_ptp_interface_add(self,name: str, ptp_instance_name: str) -> SystemPTPInterfaceOutput :
        """
        Add a PTP interface
        
        Args:
            name : name of interface
            ptp_instance_name: ptp instance name

        Returns:
        """
        cmd = f"system ptp-interface-add {name} {ptp_instance_name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_interface_add_output = SystemPTPInterfaceOutput(output)

        return system_ptp_interface_add_output

    def system_ptp_interface_delete(self,name: str) -> str :
        """
        Delete an interface
        
        Args:
            name : name or UUID of interface

        Returns:
        """
        cmd = f"system ptp-interface-delete {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        # output is a List of 1 string. "['Deleted PTP interface: xxxx-xxxx-xxx\n']"
        if output and len(output) > 0:
            return output[0].strip()
        else:
            raise "Output is expected to be a List with one element."
    
    def get_system_ptp_interface_show(self,name: str) -> SystemPTPInterfaceOutput :
        """
        Show PTP interface attributes.
        
        Args:
            name : name or UUID of interface

        Returns:
        """
        cmd = f"system ptp-interface-show {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_interface_show_output = SystemPTPInterfaceOutput(output)

        return system_ptp_interface_show_output

    def get_system_ptp_interface_list(self) -> SystemPTPInterfaceListOutput :
        """
        List all PTP interfaces

        Returns:
        """
        command = source_openrc("system ptp-interface-list")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ptp_interface_list_output = SystemPTPInterfaceListOutput(output)

        return system_ptp_interface_list_output
