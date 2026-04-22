"""Object representing compute capacity analysis for a single hypervisor."""


class OpenStackComputeCapacityObject:
    """Stores computed capacity metrics for one hypervisor.

    Holds raw data from resource provider inventory (total, used,
    allocation_ratio, reserved) plus calculated fields (effective capacity,
    headroom, utilization percentage) for vCPUs, memory, and disk.
    """

    def __init__(self):
        """Initialize OpenStackComputeCapacityObject with all fields as None."""
        self.hostname = None

        self.vcpus_total = None
        self.vcpus_used = None
        self.vcpus_allocation_ratio = None
        self.vcpus_reserved = None
        self.vcpus_effective = None
        self.vcpus_headroom = None
        self.vcpus_utilization_pct = None

        self.memory_mb_total = None
        self.memory_mb_used = None
        self.memory_mb_allocation_ratio = None
        self.memory_mb_reserved = None
        self.memory_mb_effective = None
        self.memory_mb_headroom = None
        self.memory_mb_utilization_pct = None

        self.disk_gb_total = None
        self.disk_gb_used = None
        self.disk_gb_allocation_ratio = None
        self.disk_gb_reserved = None
        self.disk_gb_effective = None
        self.disk_gb_headroom = None
        self.disk_gb_utilization_pct = None

        self.status = None

    # --- hostname ---

    def set_hostname(self, hostname: str):
        """Set the hypervisor hostname.

        Args:
            hostname (str): Hypervisor hostname.
        """
        self.hostname = hostname

    def get_hostname(self) -> str:
        """Get the hypervisor hostname.

        Returns:
            str: Hypervisor hostname.
        """
        return self.hostname

    # --- vCPUs ---

    def set_vcpus_total(self, vcpus_total: int):
        """Set the total physical vCPUs.

        Args:
            vcpus_total (int): Total physical vCPUs.
        """
        self.vcpus_total = vcpus_total

    def get_vcpus_total(self) -> int:
        """Get the total physical vCPUs.

        Returns:
            int: Total physical vCPUs.
        """
        return self.vcpus_total

    def set_vcpus_used(self, vcpus_used: int):
        """Set the used vCPUs.

        Args:
            vcpus_used (int): Used vCPUs.
        """
        self.vcpus_used = vcpus_used

    def get_vcpus_used(self) -> int:
        """Get the used vCPUs.

        Returns:
            int: Used vCPUs.
        """
        return self.vcpus_used

    def set_vcpus_allocation_ratio(self, vcpus_allocation_ratio: float):
        """Set the vCPU allocation ratio (overcommit).

        Args:
            vcpus_allocation_ratio (float): vCPU allocation ratio.
        """
        self.vcpus_allocation_ratio = vcpus_allocation_ratio

    def get_vcpus_allocation_ratio(self) -> float:
        """Get the vCPU allocation ratio (overcommit).

        Returns:
            float: vCPU allocation ratio.
        """
        return self.vcpus_allocation_ratio

    def set_vcpus_reserved(self, vcpus_reserved: int):
        """Set the reserved vCPUs.

        Args:
            vcpus_reserved (int): Reserved vCPUs.
        """
        self.vcpus_reserved = vcpus_reserved

    def get_vcpus_reserved(self) -> int:
        """Get the reserved vCPUs.

        Returns:
            int: Reserved vCPUs.
        """
        return self.vcpus_reserved

    def set_vcpus_effective(self, vcpus_effective: int):
        """Set the effective vCPU capacity (total * ratio - reserved).

        Args:
            vcpus_effective (int): Effective vCPU capacity.
        """
        self.vcpus_effective = vcpus_effective

    def get_vcpus_effective(self) -> int:
        """Get the effective vCPU capacity (total * ratio - reserved).

        Returns:
            int: Effective vCPU capacity.
        """
        return self.vcpus_effective

    def set_vcpus_headroom(self, vcpus_headroom: int):
        """Set the vCPU headroom (effective - used).

        Args:
            vcpus_headroom (int): vCPU headroom.
        """
        self.vcpus_headroom = vcpus_headroom

    def get_vcpus_headroom(self) -> int:
        """Get the vCPU headroom (effective - used).

        Returns:
            int: vCPU headroom.
        """
        return self.vcpus_headroom

    def set_vcpus_utilization_pct(self, vcpus_utilization_pct: float):
        """Set the vCPU utilization percentage.

        Args:
            vcpus_utilization_pct (float): vCPU utilization percentage.
        """
        self.vcpus_utilization_pct = vcpus_utilization_pct

    def get_vcpus_utilization_pct(self) -> float:
        """Get the vCPU utilization percentage.

        Returns:
            float: vCPU utilization percentage.
        """
        return self.vcpus_utilization_pct

    # --- Memory ---

    def set_memory_mb_total(self, memory_mb_total: int):
        """Set the total memory in MB.

        Args:
            memory_mb_total (int): Total memory in MB.
        """
        self.memory_mb_total = memory_mb_total

    def get_memory_mb_total(self) -> int:
        """Get the total memory in MB.

        Returns:
            int: Total memory in MB.
        """
        return self.memory_mb_total

    def set_memory_mb_used(self, memory_mb_used: int):
        """Set the used memory in MB.

        Args:
            memory_mb_used (int): Used memory in MB.
        """
        self.memory_mb_used = memory_mb_used

    def get_memory_mb_used(self) -> int:
        """Get the used memory in MB.

        Returns:
            int: Used memory in MB.
        """
        return self.memory_mb_used

    def set_memory_mb_allocation_ratio(self, memory_mb_allocation_ratio: float):
        """Set the memory allocation ratio (overcommit).

        Args:
            memory_mb_allocation_ratio (float): Memory allocation ratio.
        """
        self.memory_mb_allocation_ratio = memory_mb_allocation_ratio

    def get_memory_mb_allocation_ratio(self) -> float:
        """Get the memory allocation ratio (overcommit).

        Returns:
            float: Memory allocation ratio.
        """
        return self.memory_mb_allocation_ratio

    def set_memory_mb_reserved(self, memory_mb_reserved: int):
        """Set the reserved memory in MB.

        Args:
            memory_mb_reserved (int): Reserved memory in MB.
        """
        self.memory_mb_reserved = memory_mb_reserved

    def get_memory_mb_reserved(self) -> int:
        """Get the reserved memory in MB.

        Returns:
            int: Reserved memory in MB.
        """
        return self.memory_mb_reserved

    def set_memory_mb_effective(self, memory_mb_effective: int):
        """Set the effective memory capacity (total * ratio - reserved).

        Args:
            memory_mb_effective (int): Effective memory capacity in MB.
        """
        self.memory_mb_effective = memory_mb_effective

    def get_memory_mb_effective(self) -> int:
        """Get the effective memory capacity (total * ratio - reserved).

        Returns:
            int: Effective memory capacity in MB.
        """
        return self.memory_mb_effective

    def set_memory_mb_headroom(self, memory_mb_headroom: int):
        """Set the memory headroom (effective - used).

        Args:
            memory_mb_headroom (int): Memory headroom in MB.
        """
        self.memory_mb_headroom = memory_mb_headroom

    def get_memory_mb_headroom(self) -> int:
        """Get the memory headroom (effective - used).

        Returns:
            int: Memory headroom in MB.
        """
        return self.memory_mb_headroom

    def set_memory_mb_utilization_pct(self, memory_mb_utilization_pct: float):
        """Set the memory utilization percentage.

        Args:
            memory_mb_utilization_pct (float): Memory utilization percentage.
        """
        self.memory_mb_utilization_pct = memory_mb_utilization_pct

    def get_memory_mb_utilization_pct(self) -> float:
        """Get the memory utilization percentage.

        Returns:
            float: Memory utilization percentage.
        """
        return self.memory_mb_utilization_pct

    # --- Disk ---

    def set_disk_gb_total(self, disk_gb_total: int):
        """Set the total disk in GB.

        Args:
            disk_gb_total (int): Total disk in GB.
        """
        self.disk_gb_total = disk_gb_total

    def get_disk_gb_total(self) -> int:
        """Get the total disk in GB.

        Returns:
            int: Total disk in GB.
        """
        return self.disk_gb_total

    def set_disk_gb_used(self, disk_gb_used: int):
        """Set the used disk in GB.

        Args:
            disk_gb_used (int): Used disk in GB.
        """
        self.disk_gb_used = disk_gb_used

    def get_disk_gb_used(self) -> int:
        """Get the used disk in GB.

        Returns:
            int: Used disk in GB.
        """
        return self.disk_gb_used

    def set_disk_gb_allocation_ratio(self, disk_gb_allocation_ratio: float):
        """Set the disk allocation ratio (overcommit).

        Args:
            disk_gb_allocation_ratio (float): Disk allocation ratio.
        """
        self.disk_gb_allocation_ratio = disk_gb_allocation_ratio

    def get_disk_gb_allocation_ratio(self) -> float:
        """Get the disk allocation ratio (overcommit).

        Returns:
            float: Disk allocation ratio.
        """
        return self.disk_gb_allocation_ratio

    def set_disk_gb_reserved(self, disk_gb_reserved: int):
        """Set the reserved disk in GB.

        Args:
            disk_gb_reserved (int): Reserved disk in GB.
        """
        self.disk_gb_reserved = disk_gb_reserved

    def get_disk_gb_reserved(self) -> int:
        """Get the reserved disk in GB.

        Returns:
            int: Reserved disk in GB.
        """
        return self.disk_gb_reserved

    def set_disk_gb_effective(self, disk_gb_effective: int):
        """Set the effective disk capacity (total * ratio - reserved).

        Args:
            disk_gb_effective (int): Effective disk capacity in GB.
        """
        self.disk_gb_effective = disk_gb_effective

    def get_disk_gb_effective(self) -> int:
        """Get the effective disk capacity (total * ratio - reserved).

        Returns:
            int: Effective disk capacity in GB.
        """
        return self.disk_gb_effective

    def set_disk_gb_headroom(self, disk_gb_headroom: int):
        """Set the disk headroom (effective - used).

        Args:
            disk_gb_headroom (int): Disk headroom in GB.
        """
        self.disk_gb_headroom = disk_gb_headroom

    def get_disk_gb_headroom(self) -> int:
        """Get the disk headroom (effective - used).

        Returns:
            int: Disk headroom in GB.
        """
        return self.disk_gb_headroom

    def set_disk_gb_utilization_pct(self, disk_gb_utilization_pct: float):
        """Set the disk utilization percentage.

        Args:
            disk_gb_utilization_pct (float): Disk utilization percentage.
        """
        self.disk_gb_utilization_pct = disk_gb_utilization_pct

    def get_disk_gb_utilization_pct(self) -> float:
        """Get the disk utilization percentage.

        Returns:
            float: Disk utilization percentage.
        """
        return self.disk_gb_utilization_pct

    # --- Status ---

    def set_status(self, status: str):
        """Set the overall capacity status based on worst resource.

        Args:
            status (str): Capacity status ('ok', 'warning', or 'critical').
        """
        self.status = status

    def get_status(self) -> str:
        """Get the overall capacity status based on worst resource.

        Returns:
            str: Capacity status ('ok', 'warning', or 'critical').
        """
        return self.status

    def __str__(self) -> str:
        """Return human-readable capacity summary for this hypervisor.

        Returns:
            str: One-line capacity summary.
        """
        if self.vcpus_utilization_pct is None or self.memory_mb_utilization_pct is None or self.disk_gb_utilization_pct is None:
            return f"OpenStackComputeCapacityObject(hostname={self.hostname}, incomplete)"
        return f"{self.hostname}: " f"VCPU {self.vcpus_utilization_pct:.1f}% ({self.vcpus_used}/{self.vcpus_effective}) " f"| RAM {self.memory_mb_utilization_pct:.1f}% ({self.memory_mb_used}/{self.memory_mb_effective}) " f"| DISK {self.disk_gb_utilization_pct:.1f}% ({self.disk_gb_used}/{self.disk_gb_effective}) " f"[{self.status.upper()}]"
