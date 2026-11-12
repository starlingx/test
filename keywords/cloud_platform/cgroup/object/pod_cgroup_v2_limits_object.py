class PodCgroupV2LimitsObject:
    """Holds the cgroup v2 limit files read from inside a pod's container."""

    def __init__(self, cpu_weight: int, cpu_quota: int, cpu_period: int, memory_max: int) -> None:
        """Initialize PodCgroupV2LimitsObject.

        Args:
            cpu_weight (int): The cpu.weight value.
            cpu_quota (int): The quota field of cpu.max, in microseconds per period.
            cpu_period (int): The period field of cpu.max, in microseconds.
            memory_max (int): The memory.max value in bytes.
        """
        self._cpu_weight = cpu_weight
        self._cpu_quota = cpu_quota
        self._cpu_period = cpu_period
        self._memory_max = memory_max

    def get_cpu_weight(self) -> int:
        """Get the cpu.weight value.

        Returns:
            int: The cpu.weight value.
        """
        return self._cpu_weight

    def get_cpu_quota(self) -> int:
        """Get the quota field of cpu.max.

        Returns:
            int: The CPU quota in microseconds per period.
        """
        return self._cpu_quota

    def get_cpu_period(self) -> int:
        """Get the period field of cpu.max.

        Returns:
            int: The CFS period in microseconds.
        """
        return self._cpu_period

    def get_memory_max(self) -> int:
        """Get the memory.max value.

        Returns:
            int: The memory.max value in bytes.
        """
        return self._memory_max

    def __str__(self) -> str:
        """Return a readable summary of the limits.

        Returns:
            str: The cpu.weight, cpu.max (quota and period) and memory.max values.
        """
        return f"PodCgroupV2LimitsObject(cpu.weight={self._cpu_weight}, cpu.max='{self._cpu_quota} {self._cpu_period}', memory.max={self._memory_max})"
