"""Module for the 'system host-disk' command keywords."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_disk_output import SystemHostDiskOutput


class SystemHostDiskKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'system host-disk-*' commands."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the SystemHostDiskKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_system_host_disk_list(self, hostname: str) -> SystemHostDiskOutput:
        """
        Get the system host disk list.

        Args:
            hostname (str): Name of the host for which we want to get the disk list.

        Returns:
            SystemHostDiskOutput: object with the list of host disks.
        """
        output = self.ssh_connection.send(source_openrc(f"system host-disk-list --nowrap {hostname}"))
        self.validate_success_return_code(self.ssh_connection)
        system_host_cpu_output = SystemHostDiskOutput(output)

        return system_host_cpu_output
