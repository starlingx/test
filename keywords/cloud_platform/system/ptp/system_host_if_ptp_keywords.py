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

    def system_host_if_ptp_assign(self, hostname: str, interface: str, ptp_interface: str) -> SystemHostIfPTPAssignOutput:
        """
        Associate PTP to an interface at host.

        Args:
            hostname (str): Hostname or id to assign the interface to
            interface (str): Host's interface name or uuid to assign ptp interface to
            ptp_interface (str): PTP interface name or uuid to assign

        Returns:
            SystemHostIfPTPAssignOutput: Output of the command
        """
        cmd = f"system host-if-ptp-assign {hostname} {interface} {ptp_interface}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_host_if_ptp_assign_output = SystemHostIfPTPAssignOutput(output)

        return system_host_if_ptp_assign_output

    def system_host_if_ptp_assign_with_error(self, hostname: str, interface: str, ptp_interface: str) -> str:
        """
        Associate PTP to an interface at host for errors.

        Args:
            hostname (str): Hostname or id to assign the interface to
            interface (str): Host's interface name or uuid to assign ptp interface to
            ptp_interface (str): PTP interface name or uuid to assign

        Returns:
            str: Output of the command

        Raises:
            Exception: If the command fails with an error message
        """
        cmd = f"system host-if-ptp-assign {hostname} {interface} {ptp_interface}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def system_host_if_ptp_remove(self, hostname: str, interface: str, ptp_interface: str) -> SystemHostIfPTPAssignOutput:
        """
        Disassociate PTP to an interface at host.

        Args:
            hostname (str): Hostname or id to disassociate ptp interface from
            interface (str): Host's interface name or uuid to disassociate ptp interface from
            ptp_interface (str): PTP interface name or uuid to disassociate

        Returns:
            SystemHostIfPTPAssignOutput: Output of the command
        """
        cmd = f"system host-if-ptp-remove {hostname} {interface} {ptp_interface}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)

        self.validate_success_return_code(self.ssh_connection)
        system_host_if_ptp_remove_output = SystemHostIfPTPAssignOutput(output)

        return system_host_if_ptp_remove_output

    def system_host_if_ptp_remove_with_error(self, hostname: str, interface: str, ptp_interface: str) -> str:
        """
        Disassociate PTP to an interface at host for errors.

        Args:
            hostname (str): Hostname or id to disassociate ptp interface from
            interface (str): Host's interface name or uuid to disassociate ptp interface from
            ptp_interface (str): PTP interface name or uuid to disassociate

        Returns:
            str: Output of the command
        """
        cmd = f"system host-if-ptp-remove {hostname} {interface} {ptp_interface}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        if isinstance(output, list) and len(output) > 0:
            return output[0].strip()
        return output.strip() if isinstance(output, str) else str(output)

    def get_system_host_if_ptp_list(self, hostname: str) -> SystemHostIfPTPListOutput:
        """
        List all PTP interfaces on the specified host

        Args:
            hostname (str): Hostname or id
        Returns:
            SystemHostIfPTPListOutput: system host if ptp list output
        """
        command = source_openrc(f"system host-if-ptp-list --nowrap {hostname}")
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_if_ptp_list_output = SystemHostIfPTPListOutput(output)

        return system_host_if_ptp_list_output
