from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ptp.objects.system_host_ptp_instance_output import SystemHostPTPInstanceOutput

class SystemHostPTPInstanceKeywords(BaseKeyword):
    """
    Provides methods to interact with the system host-ptp-instance
    using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the SystemHostPTPInstanceKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def system_host_ptp_instance_assign(self,hostname: str, name: str) -> SystemHostPTPInstanceOutput :
        """
        Assign the ptp instance to a host
        
        Args:
            hostname : hostname or id to assign the ptp instance to host
            name: name or UUID for ptp instance assign

        Returns:
        """
        cmd = f"system host-ptp-instance-assign {hostname} {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_ptp_instance_assign_output = SystemHostPTPInstanceOutput(output)

        return system_host_ptp_instance_assign_output

    def system_host_ptp_instance_remove(self,hostname: str, name: str) -> SystemHostPTPInstanceOutput :
        """
        Remove host association
        
        Args:
            hostname : hostname or id
            name: name or UUID for ptp instance name

        Returns:
        """
        cmd = f"system host-ptp-instance-remove {hostname} {name}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_ptp_instance_remove_output = SystemHostPTPInstanceOutput(output)

        return system_host_ptp_instance_remove_output
    
    def get_system_host_ptp_instance_list(self,hostname: str) -> SystemHostPTPInstanceOutput :
        """
        List all PTP instances on the specified host
        
        Args:
            hostname : hostname or id

        Returns:
        """
        cmd = f"system host-ptp-instance-list {hostname}"
        command = source_openrc(cmd)
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_host_ptp_instance_list_output = SystemHostPTPInstanceOutput(output)

        return system_host_ptp_instance_list_output