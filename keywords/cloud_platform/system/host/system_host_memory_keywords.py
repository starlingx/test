from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_memory_output import SystemHostMemoryOutput


class SystemHostMemoryKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-memory-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_memory_list(self, hostname) -> SystemHostMemoryOutput:
        """
        Gets the system host memory list

        Args:
            hostname: Name of the host for which we want to get the memory list.

        Returns:

        """
        output = self.ssh_connection.send(source_openrc(f'system host-memory-list --nowrap {hostname}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_cpu_output = SystemHostMemoryOutput(output)

        return system_host_cpu_output

    def system_host_memory_modify(
        self,
        hostname: str,
        processor: int,
        hugepages_1g: int = None,
        hugepages_2m: int = None,
    ) -> None:
        """Modify memory allocation for a host processor/NUMA node.

        Runs: system host-memory-modify <hostname> <processor> [-1G <count>] [-2M <count>]

        At least one of hugepages_1g or hugepages_2m must be provided.
        The host must be locked for this change to take effect.

        Args:
            hostname (str): Host to modify.
            processor (int): Processor/NUMA node number (e.g. 0, 1).
            hugepages_1g (int): Number of 1G hugepages to allocate. Optional.
            hugepages_2m (int): Number of 2M hugepages to allocate. Optional.

        Raises:
            ValueError: If neither hugepages_1g nor hugepages_2m is provided.
        """
        if hugepages_1g is None and hugepages_2m is None:
            raise ValueError("At least one of hugepages_1g or hugepages_2m must be provided")

        args = ""
        if hugepages_1g is not None:
            args += f" -1G {hugepages_1g}"
        if hugepages_2m is not None:
            args += f" -2M {hugepages_2m}"

        cmd = source_openrc(f"system host-memory-modify {hostname} {processor}{args}")
        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)
