"""OpenStack resource provider inventory list data object."""


class OpenStackResourceProviderInventoryListObject:
    """Object to represent the output of the 'openstack resource provider inventory list' command."""

    def __init__(self):
        """Initialize OpenStackResourceProviderInventoryListObject."""
        self.resource_class = None
        self.allocation_ratio = None
        self.min_unit = None
        self.max_unit = None
        self.reserved = None
        self.step_size = None
        self.total = None
        self.used = None

    def set_resource_class(self, resource_class: str):
        """
        Set the resource class.

        Args:
            resource_class (str): resource class.
        """
        self.resource_class = resource_class

    def get_resource_class(self) -> str:
        """
        Get the resource class.

        Returns:
            str: resource class.
        """
        return self.resource_class

    def set_allocation_ratio(self, allocation_ratio: float):
        """
        Set the allocation ratio.

        Args:
            allocation_ratio (float): allocation ratio.
        """
        self.allocation_ratio = allocation_ratio

    def get_allocation_ratio(self) -> float:
        """
        Get the allocation ratio.

        Returns:
            float: allocation ratio.
        """
        return self.allocation_ratio

    def set_min_unit(self, min_unit: int):
        """
        Set the min unit.

        Args:
            min_unit (int): min unit.
        """
        self.min_unit = min_unit

    def get_min_unit(self) -> int:
        """
        Get the min unit.

        Returns:
            int: min unit.
        """
        return self.min_unit

    def set_max_unit(self, max_unit: int):
        """
        Set the max unit.

        Args:
            max_unit (int): max unit.
        """
        self.max_unit = max_unit

    def get_max_unit(self) -> int:
        """
        Get the max unit.

        Returns:
            int: max unit.
        """
        return self.max_unit

    def set_reserved(self, reserved: int):
        """
        Set the reserved.

        Args:
            reserved (int): reserved.
        """
        self.reserved = reserved

    def get_reserved(self) -> int:
        """
        Get the reserved.

        Returns:
            int: reserved.
        """
        return self.reserved

    def set_step_size(self, step_size: int):
        """
        Set the step size.

        Args:
            step_size (int): step size.
        """
        self.step_size = step_size

    def get_step_size(self) -> int:
        """
        Get the step size.

        Returns:
            int: step size.
        """
        return self.step_size

    def set_total(self, total: int):
        """
        Set the total.

        Args:
            total (int): total.
        """
        self.total = total

    def get_total(self) -> int:
        """
        Get the total.

        Returns:
            int: total.
        """
        return self.total

    def set_used(self, used: int):
        """
        Set the used.

        Args:
            used (int): used.
        """
        self.used = used

    def get_used(self) -> int:
        """
        Get the used.

        Returns:
            int: used.
        """
        return self.used

    def __str__(self) -> str:
        """
        Return human-readable representation.

        Returns:
            str: Human-readable resource provider inventory list summary.
        """
        return f"OpenStackResourceProviderInventoryListObject(" f"resource_class={self.resource_class}, " f"allocation_ratio={self.allocation_ratio}, " f"min_unit={self.min_unit}, " f"max_unit={self.max_unit}, " f"reserved={self.reserved}, " f"step_size={self.step_size}, " f"total={self.total}, " f"used={self.used}" ")"
