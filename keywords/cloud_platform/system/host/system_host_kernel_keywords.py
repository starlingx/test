from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from starlingx.keywords.cloud_platform.system.host.objects.system_host_kernel_show_output import SystemHostKernelShowOutput


class SystemHostKernelKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-kernel-show/modify <controller-id/hostname>' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSH connection for the host
        """
        self.ssh_connection = ssh_connection

    def get_system_host_kernel_show(self, hostname: str) -> str:
        """
        Gets the system host port show

        Args:
            hostname (str): Name of the host for which we want to get the kernel.

        Returns:
            str: output of the command
        """
        output = self.ssh_connection.send(source_openrc(f"system host-kernel-show {hostname}"))
        self.validate_success_return_code(self.ssh_connection)
        system_host_port_output = SystemHostKernelShowOutput(output)

        return system_host_port_output

    def get_running_kernel(self, hostname: str) -> str:
        """
        Gets the running kernel for a host.

        Args:
            hostname(str): Name of the host

        Returns:
            str: Running kernel value
        """
        kernel_show_output = self.get_system_host_kernel_show(hostname)
        return kernel_show_output.get_host_kernel_show().get_kernel_running()

    def modify_kernel_config(self, hostname: str, kernel_value: str) -> None:
        """
        Modifies the kernel config for a given host.

        Args:
            hostname(str): Name of the host for which we want to modify the kernel.
            kernel_value(str): Value of the kernel we want to set.

        """
        self.ssh_connection.send(source_openrc(f"system host-kernel-modify {hostname} {kernel_value}"))
        self.validate_success_return_code(self.ssh_connection)
