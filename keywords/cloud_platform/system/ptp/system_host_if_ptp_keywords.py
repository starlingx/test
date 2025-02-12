from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_host_if_ptp_assign_output import SystemHostIfPTPAssignOutput
from keywords.cloud_platform.system.ptp.objects.system_host_if_ptp_list_output import SystemHostIfPTPListOutput

class SystemHostIfPTPKeywords(BaseKeyword):
    """
    Provides methods to interact with the system host-if-ptp-instance
    using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SystemHostIfPTPKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def system_host_if_ptp_assign(self,hostname: str, interface: str, ptp_interface: str) -> SystemHostIfPTPAssignOutput :
        """
        Associate PTP to an interface at host.
        
        Args:
            hostname: Hostname or id to assign the interface to
            interface: Host's interface name or uuid to assign ptp interface to
            ptp_interface: PTP interface name or uuid to assign

        Returns:
        """
        cmd = f"system host-if-ptp-assign {hostname} {interface} {ptp_interface}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_if_ptp_assign_output = SystemHostIfPTPAssignOutput(output)

        return system_host_if_ptp_assign_output

    def system_host_if_ptp_remove(self,hostname: str, interface: str, ptp_interface: str) -> SystemHostIfPTPAssignOutput :
        """
        Disassociate PTP to an interface at host.
        
        Args:
            hostname: Hostname or id to disassociate ptp interface from
            interface: Host's interface name or uuid to disassociate ptp interface from
            ptp_interface: PTP interface name or uuid to disassociate

        Returns:
        """
        cmd = f"system host-if-ptp-remove {hostname} {interface} {ptp_interface}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_if_ptp_remove_output = SystemHostIfPTPAssignOutput(output)

        return system_host_if_ptp_remove_output

    def get_system_host_if_ptp_list(self,hostname: str) -> SystemHostIfPTPListOutput :
        """
        List all PTP interfaces on the specified host
        
        Args:
            hostname: Hostname or id
        Returns:
        """
        command = source_openrc(f'system host-if-ptp-list --nowrap {hostname}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_if_ptp_list_output = SystemHostIfPTPListOutput(output)

        return system_host_if_ptp_list_output
        
