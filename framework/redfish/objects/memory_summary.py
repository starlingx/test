from framework.redfish.objects.status import Status


class MemorySummary:
    """Represents system memory summary information."""

    def __init__(self, total_system_memory_gib: int, memory_mirroring: str, status: Status):
        """Initialize MemorySummary object.

        Args:
            total_system_memory_gib (int): Total system memory in GiB.
            memory_mirroring (str): Memory mirroring configuration.
            status (Status): Memory status object.
        """
        self.total_system_memory_gib = total_system_memory_gib
        self.memory_mirroring = memory_mirroring
        self.status = status

    def get_total_system_memory_gib(self) -> int:
        """Get total system memory in GiB.

        Returns:
            int: Total system memory in GiB.
        """
        return self.total_system_memory_gib

    def set_total_system_memory_gib(self, total_system_memory_gib: int) -> None:
        """Set total system memory in GiB.

        Args:
            total_system_memory_gib (int): Total system memory in GiB.
        """
        self.total_system_memory_gib = total_system_memory_gib

    def get_memory_mirroring(self) -> str:
        """Get memory mirroring configuration.

        Returns:
            str: Memory mirroring configuration.
        """
        return self.memory_mirroring

    def set_memory_mirroring(self, memory_mirroring: str) -> None:
        """Set memory mirroring configuration.

        Args:
            memory_mirroring (str): Memory mirroring configuration.
        """
        self.memory_mirroring = memory_mirroring

    def get_status(self) -> Status:
        """Get memory status.

        Returns:
            Status: Memory status object.
        """
        return self.status

    def set_status(self, status: Status) -> None:
        """Set memory status.

        Args:
            status (Status): Memory status object.
        """
        self.status = status
