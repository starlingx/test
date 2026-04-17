"""OpenStack hypervisor stats data object."""


class OpenStackHypervisorStatsObject:
    """Object to represent the output of the 'openstack hypervisor stats show' command."""

    def __init__(self):
        """Initialize OpenStackHypervisorStatsObject."""
        self.count = None
        self.current_workload = None
        self.disk_available_least = None
        self.free_disk_gb = None
        self.free_ram_mb = None
        self.local_gb = None
        self.local_gb_used = None
        self.memory_mb = None
        self.memory_mb_used = None
        self.running_vms = None
        self.vcpus = None
        self.vcpus_used = None

    def set_count(self, count: int):
        """
        Set the count of hypervisors.

        Args:
            count (int): count of hypervisors.
        """
        self.count = count

    def get_count(self) -> int:
        """
        Get the count of hypervisors.

        Returns:
            int: count of hypervisors.
        """
        return self.count

    def set_current_workload(self, current_workload: int):
        """
        Set the current workload.

        Args:
            current_workload (int): current workload.
        """
        self.current_workload = current_workload

    def get_current_workload(self) -> int:
        """
        Get the current workload.

        Returns:
            int: current workload.
        """
        return self.current_workload

    def set_disk_available_least(self, disk_available_least: int):
        """
        Set the least available disk space in GB.

        Args:
            disk_available_least (int): least available disk space in GB.
        """
        self.disk_available_least = disk_available_least

    def get_disk_available_least(self) -> int:
        """
        Get the least available disk space in GB.

        Returns:
            int: least available disk space in GB.
        """
        return self.disk_available_least

    def set_free_disk_gb(self, free_disk_gb: int):
        """
        Set the amount of free disk space in GB.

        Args:
            free_disk_gb (int): amount of free disk space in GB.
        """
        self.free_disk_gb = free_disk_gb

    def get_free_disk_gb(self) -> int:
        """
        Get the amount of free disk space in GB.

        Returns:
            int: amount of free disk space in GB.
        """
        return self.free_disk_gb

    def set_free_ram_mb(self, free_ram_mb: int):
        """
        Set the amount of free RAM in MB.

        Args:
            free_ram_mb (int): amount of free RAM in MB.
        """
        self.free_ram_mb = free_ram_mb

    def get_free_ram_mb(self) -> int:
        """
        Get the amount of free RAM in MB.

        Returns:
            int: amount of free RAM in MB.
        """
        return self.free_ram_mb

    def set_local_gb(self, local_gb: int):
        """
        Set the amount of local disk space in GB.

        Args:
            local_gb (int): amount of local disk space in GB.
        """
        self.local_gb = local_gb

    def get_local_gb(self) -> int:
        """
        Get the amount of local disk space in GB.

        Returns:
            int: amount of local disk space in GB.
        """
        return self.local_gb

    def set_local_gb_used(self, local_gb_used: int):
        """
        Set the amount of used local disk space in GB.

        Args:
            local_gb_used (int): amount of used local disk space in GB.
        """
        self.local_gb_used = local_gb_used

    def get_local_gb_used(self) -> int:
        """
        Get the amount of used local disk space in GB.

        Returns:
            int: amount of used local disk space in GB.
        """
        return self.local_gb_used

    def set_memory_mb(self, memory_mb: int):
        """
        Set the amount of memory in MB.

        Args:
            memory_mb (int): amount of memory in MB.
        """
        self.memory_mb = memory_mb

    def get_memory_mb(self) -> int:
        """
        Get the amount of memory in MB.

        Returns:
            int: amount of memory in MB.
        """
        return self.memory_mb

    def set_memory_mb_used(self, memory_mb_used: int):
        """
        Set the amount of used memory in MB.

        Args:
            memory_mb_used (int): amount of used memory in MB.
        """
        self.memory_mb_used = memory_mb_used

    def get_memory_mb_used(self) -> int:
        """
        Get the amount of used memory in MB.

        Returns:
            int: amount of used memory in MB.
        """
        return self.memory_mb_used

    def set_running_vms(self, running_vms: int):
        """
        Set the number of running VMs.

        Args:
            running_vms (int): number of running VMs.
        """
        self.running_vms = running_vms

    def get_running_vms(self) -> int:
        """
        Get the number of running VMs.

        Returns:
            int: number of running VMs.
        """
        return self.running_vms

    def set_vcpus(self, vcpus: int):
        """
        Set the number of vCPUs.

        Args:
            vcpus (int): number of vCPUs.
        """
        self.vcpus = vcpus

    def get_vcpus(self) -> int:
        """
        Get the number of vCPUs.

        Returns:
            int: number of vCPUs.
        """
        return self.vcpus

    def set_vcpus_used(self, vcpus_used: int):
        """
        Set the number of used vCPUs.

        Args:
            vcpus_used (int): number of used vCPUs.
        """
        self.vcpus_used = vcpus_used

    def get_vcpus_used(self) -> int:
        """
        Get the number of used vCPUs.

        Returns:
            int: number of used vCPUs.
        """
        return self.vcpus_used

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable hypervisor stats summary.
        """
        return f"HypervisorStats(count={self.count}, vcpus={self.vcpus}/{self.vcpus_used} used, " f"memory_mb={self.memory_mb}/{self.memory_mb_used} used, " f"local_gb={self.local_gb}/{self.local_gb_used} used, " f"running_vms={self.running_vms})"
