from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_cpu_output import SystemHostCPUOutput
from keywords.cloud_platform.system.host.objects.system_host_cpu_show_output import SystemHostCPUShowOutput


class SystemHostCPUKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-cpu-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_cpu_list(self, hostname) -> SystemHostCPUOutput:
        """
        Gets the system host cpu list

        Args:
            hostname: Name of the host for which we want to get the cpu list.

        Returns:

        """
        output = self.ssh_connection.send(source_openrc(f'system host-cpu-list --nowrap {hostname}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_cpu_output = SystemHostCPUOutput(output)

        return system_host_cpu_output

    def system_host_cpu_modify(self, hostname: str, function: str, num_cores_on_processor_0: int = -1, num_cores_on_processor_1: int = -1) -> SystemHostCPUOutput:
        """
        Run the "system host-cpu-modify" command with the specified arguments.

        Args:
            hostname: Name of the host to modify.
            function: Name of the function (-f) that we want to set. e.g. vswitch, shared
            num_cores_on_processor_0: (-p0) Number of Cores on Processor 0. Will ignore this parameter if set to -1.
            num_cores_on_processor_1: (-p1) Number of Cores on Processor 1. Will ignore this parameter if set to -1.

        Returns:

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

    def get_system_host_cpu_show(self, host_id, cpu_uuid) -> SystemHostCPUShowOutput:
        """
        Gets the system host cpu show

        Args:
            host_id: ID of host for which we want to get the cpu details.
            cpu_uuid: UUID of the CPU

        Returns:

        """
        output = self.ssh_connection.send(source_openrc(f'system host-cpu-show {host_id} {cpu_uuid}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_cpu_output = SystemHostCPUShowOutput(output)

        return system_host_cpu_output
