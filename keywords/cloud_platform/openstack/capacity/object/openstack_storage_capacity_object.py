"""Object representing storage capacity analysis for a single Cinder pool."""


class OpenStackStorageCapacityObject:
    """Stores computed capacity metrics for one Cinder storage pool.

    Holds raw data from cinder get-pools (total, free, allocated,
    oversubscription ratio, reserved percentage) plus calculated fields
    (effective capacity, headroom, utilization percentage, status).
    """

    def __init__(self):
        """Initialize OpenStackStorageCapacityObject with all fields as None."""
        self.pool_name = None
        self.backend_name = None

        self.total_capacity_gb = None
        self.free_capacity_gb = None
        self.allocated_capacity_gb = None
        self.max_over_subscription_ratio = None
        self.reserved_percentage = None

        self.effective_capacity_gb = None
        self.headroom_gb = None
        self.utilization_pct = None

        self.status = None

    # --- Pool identification ---

    def set_pool_name(self, pool_name: str):
        """Set the pool name.

        Args:
            pool_name (str): Pool name.
        """
        self.pool_name = pool_name

    def get_pool_name(self) -> str:
        """Get the pool name.

        Returns:
            str: Pool name.
        """
        return self.pool_name

    def set_backend_name(self, backend_name: str):
        """Set the volume backend name.

        Args:
            backend_name (str): Volume backend name.
        """
        self.backend_name = backend_name

    def get_backend_name(self) -> str:
        """Get the volume backend name.

        Returns:
            str: Volume backend name.
        """
        return self.backend_name

    # --- Raw data from cinder ---

    def set_total_capacity_gb(self, total_capacity_gb: float):
        """Set the total capacity in GB.

        Args:
            total_capacity_gb (float): Total capacity in GB.
        """
        self.total_capacity_gb = total_capacity_gb

    def get_total_capacity_gb(self) -> float:
        """Get the total capacity in GB.

        Returns:
            float: Total capacity in GB.
        """
        return self.total_capacity_gb

    def set_free_capacity_gb(self, free_capacity_gb: float):
        """Set the free capacity in GB.

        Args:
            free_capacity_gb (float): Free capacity in GB.
        """
        self.free_capacity_gb = free_capacity_gb

    def get_free_capacity_gb(self) -> float:
        """Get the free capacity in GB.

        Returns:
            float: Free capacity in GB.
        """
        return self.free_capacity_gb

    def set_allocated_capacity_gb(self, allocated_capacity_gb: float):
        """Set the allocated capacity in GB.

        Args:
            allocated_capacity_gb (float): Allocated capacity in GB.
        """
        self.allocated_capacity_gb = allocated_capacity_gb

    def get_allocated_capacity_gb(self) -> float:
        """Get the allocated capacity in GB.

        Returns:
            float: Allocated capacity in GB.
        """
        return self.allocated_capacity_gb

    def set_max_over_subscription_ratio(self, max_over_subscription_ratio: float):
        """Set the max over subscription ratio.

        Args:
            max_over_subscription_ratio (float): Max over subscription ratio.
        """
        self.max_over_subscription_ratio = max_over_subscription_ratio

    def get_max_over_subscription_ratio(self) -> float:
        """Get the max over subscription ratio.

        Returns:
            float: Max over subscription ratio.
        """
        return self.max_over_subscription_ratio

    def set_reserved_percentage(self, reserved_percentage: int):
        """Set the reserved percentage.

        Args:
            reserved_percentage (int): Reserved percentage.
        """
        self.reserved_percentage = reserved_percentage

    def get_reserved_percentage(self) -> int:
        """Get the reserved percentage.

        Returns:
            int: Reserved percentage.
        """
        return self.reserved_percentage

    # --- Calculated fields ---

    def set_effective_capacity_gb(self, effective_capacity_gb: float):
        """Set the effective capacity in GB.

        Calculated as: total * max_over_subscription_ratio * (1 - reserved_percentage / 100).

        Args:
            effective_capacity_gb (float): Effective capacity in GB.
        """
        self.effective_capacity_gb = effective_capacity_gb

    def get_effective_capacity_gb(self) -> float:
        """Get the effective capacity in GB.

        Returns:
            float: Effective capacity in GB.
        """
        return self.effective_capacity_gb

    def set_headroom_gb(self, headroom_gb: float):
        """Set the storage headroom in GB (effective - allocated).

        Args:
            headroom_gb (float): Storage headroom in GB.
        """
        self.headroom_gb = headroom_gb

    def get_headroom_gb(self) -> float:
        """Get the storage headroom in GB (effective - allocated).

        Returns:
            float: Storage headroom in GB.
        """
        return self.headroom_gb

    def set_utilization_pct(self, utilization_pct: float):
        """Set the storage utilization percentage.

        Args:
            utilization_pct (float): Storage utilization percentage.
        """
        self.utilization_pct = utilization_pct

    def get_utilization_pct(self) -> float:
        """Get the storage utilization percentage.

        Returns:
            float: Storage utilization percentage.
        """
        return self.utilization_pct

    # --- Status ---

    def set_status(self, status: str):
        """Set the capacity status for this pool.

        Args:
            status (str): Capacity status ('ok', 'warning', or 'critical').
        """
        self.status = status

    def get_status(self) -> str:
        """Get the capacity status for this pool.

        Returns:
            str: Capacity status ('ok', 'warning', or 'critical').
        """
        return self.status

    def __str__(self) -> str:
        """Return human-readable capacity summary for this storage pool.

        Returns:
            str: One-line capacity summary.
        """
        if self.utilization_pct is None or self.effective_capacity_gb is None:
            return f"OpenStackStorageCapacityObject(pool_name={self.pool_name}, incomplete)"
        return f"{self.backend_name}: " f"{self.utilization_pct:.1f}% " f"({self.allocated_capacity_gb:.1f}/{self.effective_capacity_gb:.1f} GB) " f"[{self.status.upper()}]"
