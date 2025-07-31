from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_cpu_output import SystemHostCPUOutput
from keywords.cloud_platform.system.host.objects.system_host_cpu_show_output import SystemHostCPUShowOutput


class SystemHostCPUKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-cpu-*' commands.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor for SystemHostCPUKeywords.

        Args:
            ssh_connection (SSHConnection): An active SSH connection to the target system,
                used for executing system commands.
        """
        self.ssh_connection = ssh_connection

    def get_system_host_cpu_list(self, hostname: str) -> SystemHostCPUOutput:
        """
        Gets the system host CPU list.

        Args:
            hostname (str): Name of the host for which we want to get the CPU list.

        Returns:
            SystemHostCPUOutput: An object containing the parsed CPU list for the specified host.
        """
        output = self.ssh_connection.send(source_openrc(f"system host-cpu-list --nowrap {hostname}"))
        self.validate_success_return_code(self.ssh_connection)
        system_host_cpu_output = SystemHostCPUOutput(output)

        return system_host_cpu_output

    def system_host_cpu_modify(self, hostname: str, function: str, num_cores_on_processor_0: int = -1, num_cores_on_processor_1: int = -1) -> SystemHostCPUOutput:
        """
        Run the "system host-cpu-modify" command with the specified arguments.

        Args:
            hostname (str): Name of the host to modify.
            function (str): Name of the function (-f) that we want to set. For example: `vswitch`, `shared`.
            num_cores_on_processor_0 (int, optional): Number of cores on Processor 0 (`-p0`). Ignored if set to `-1`.
            num_cores_on_processor_1 (int, optional): Number of cores on Processor 1 (`-p1`). Ignored if set to `-1`.

        Returns:
            SystemHostCPUOutput: Parsed output of the `system host-cpu-modify` command.
        """
        num_cores_argument = ""
        if num_cores_on_processor_0 >= 0:
            num_cores_argument += f"-p0 {num_cores_on_processor_0} "
        if num_cores_on_processor_1 >= 0:
            num_cores_argument += f"-p1 {num_cores_on_processor_1} "

        cmd = f"system host-cpu-modify --nowrap -f {function} {num_cores_argument} {hostname}"
        output = self.ssh_connection.send(source_openrc(cmd))

        self.validate_success_return_code(self.ssh_connection)
        system_host_cpu_output = SystemHostCPUOutput(output)

        return system_host_cpu_output

    def get_system_host_cpu_show(self, host_id: str, cpu_uuid: str) -> SystemHostCPUShowOutput:
        """
        Gets the details of a specific CPU from a given host.

        Args:
            host_id (str): ID of the host for which to retrieve CPU details.
            cpu_uuid (str): UUID of the CPU.

        Returns:
            SystemHostCPUShowOutput: Parsed output containing the CPU details.
        """
        output = self.ssh_connection.send(source_openrc(f"system host-cpu-show {host_id} {cpu_uuid}"))
        self.validate_success_return_code(self.ssh_connection)
        system_host_cpu_output = SystemHostCPUShowOutput(output)

        return system_host_cpu_output
