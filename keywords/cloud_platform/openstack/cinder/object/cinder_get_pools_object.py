"""Cinder get-pools data object."""


class CinderGetPoolsObject:
    """Object to represent a storage pool from the 'cinder get-pools --detail' command."""

    def __init__(self):
        """Initialize CinderGetPoolsObject."""
        self.name = None
        self.total_capacity_gb = None
        self.free_capacity_gb = None
        self.allocated_capacity_gb = None
        self.max_over_subscription_ratio = None
        self.reserved_percentage = None
        self.backend_state = None
        self.storage_protocol = None
        self.volume_backend_name = None
        self.thin_provisioning_support = None
        self.multiattach = None
        self.driver_version = None
        self.vendor_name = None
        self.replication_enabled = None
        self.qos_support = None
        self.timestamp = None

    def set_name(self, name: str):
        """Set the pool name.

        Args:
            name (str): Pool name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get the pool name.

        Returns:
            str: Pool name.
        """
        return self.name

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

    def set_backend_state(self, backend_state: str):
        """Set the backend state.

        Args:
            backend_state (str): Backend state.
        """
        self.backend_state = backend_state

    def get_backend_state(self) -> str:
        """Get the backend state.

        Returns:
            str: Backend state.
        """
        return self.backend_state

    def set_storage_protocol(self, storage_protocol: str):
        """Set the storage protocol.

        Args:
            storage_protocol (str): Storage protocol.
        """
        self.storage_protocol = storage_protocol

    def get_storage_protocol(self) -> str:
        """Get the storage protocol.

        Returns:
            str: Storage protocol.
        """
        return self.storage_protocol

    def set_volume_backend_name(self, volume_backend_name: str):
        """Set the volume backend name.

        Args:
            volume_backend_name (str): Volume backend name.
        """
        self.volume_backend_name = volume_backend_name

    def get_volume_backend_name(self) -> str:
        """Get the volume backend name.

        Returns:
            str: Volume backend name.
        """
        return self.volume_backend_name

    def set_thin_provisioning_support(self, thin_provisioning_support: bool):
        """Set the thin provisioning support flag.

        Args:
            thin_provisioning_support (bool): Thin provisioning support.
        """
        self.thin_provisioning_support = thin_provisioning_support

    def get_thin_provisioning_support(self) -> bool:
        """Get the thin provisioning support flag.

        Returns:
            bool: Thin provisioning support.
        """
        return self.thin_provisioning_support

    def set_multiattach(self, multiattach: bool):
        """Set the multiattach flag.

        Args:
            multiattach (bool): Multiattach support.
        """
        self.multiattach = multiattach

    def get_multiattach(self) -> bool:
        """Get the multiattach flag.

        Returns:
            bool: Multiattach support.
        """
        return self.multiattach

    def set_driver_version(self, driver_version: str):
        """Set the driver version.

        Args:
            driver_version (str): Driver version.
        """
        self.driver_version = driver_version

    def get_driver_version(self) -> str:
        """Get the driver version.

        Returns:
            str: Driver version.
        """
        return self.driver_version

    def set_vendor_name(self, vendor_name: str):
        """Set the vendor name.

        Args:
            vendor_name (str): Vendor name.
        """
        self.vendor_name = vendor_name

    def get_vendor_name(self) -> str:
        """Get the vendor name.

        Returns:
            str: Vendor name.
        """
        return self.vendor_name

    def set_replication_enabled(self, replication_enabled: bool):
        """Set the replication enabled flag.

        Args:
            replication_enabled (bool): Replication enabled.
        """
        self.replication_enabled = replication_enabled

    def get_replication_enabled(self) -> bool:
        """Get the replication enabled flag.

        Returns:
            bool: Replication enabled.
        """
        return self.replication_enabled

    def set_qos_support(self, qos_support: bool):
        """Set the QoS support flag.

        Args:
            qos_support (bool): QoS support.
        """
        self.qos_support = qos_support

    def get_qos_support(self) -> bool:
        """Get the QoS support flag.

        Returns:
            bool: QoS support.
        """
        return self.qos_support

    def set_timestamp(self, timestamp: str):
        """Set the timestamp.

        Args:
            timestamp (str): Timestamp.
        """
        self.timestamp = timestamp

    def get_timestamp(self) -> str:
        """Get the timestamp.

        Returns:
            str: Timestamp.
        """
        return self.timestamp

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable cinder pool summary.
        """
        return f"CinderGetPoolsObject(" f"name={self.name}, " f"total_capacity_gb={self.total_capacity_gb}, " f"free_capacity_gb={self.free_capacity_gb}, " f"allocated_capacity_gb={self.allocated_capacity_gb}, " f"backend_state={self.backend_state}, " f"storage_protocol={self.storage_protocol})"
