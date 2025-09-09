from framework.redfish.objects.status import Status


class ProcessorSummary:
    """Represents processor summary information."""

    def __init__(self, core_count: int, count: int, logical_processor_count: int, model: str, threading_enabled: bool, status: Status):
        """Initialize ProcessorSummary object.

        Args:
            core_count (int): Number of processor cores.
            count (int): Number of processors.
            logical_processor_count (int): Number of logical processors.
            model (str): Processor model name.
            threading_enabled (bool): Whether threading is enabled.
            status (Status): Processor status object.
        """
        self.core_count = core_count
        self.count = count
        self.logical_processor_count = logical_processor_count
        self.model = model
        self.threading_enabled = threading_enabled
        self.status = status

    def get_core_count(self) -> int:
        """Get core count.

        Returns:
            int: Number of processor cores.
        """
        return self.core_count

    def set_core_count(self, core_count: int) -> None:
        """Set core count.

        Args:
            core_count (int): Number of processor cores.
        """
        self.core_count = core_count

    def get_count(self) -> int:
        """Get processor count.

        Returns:
            int: Number of processors.
        """
        return self.count

    def set_count(self, count: int) -> None:
        """Set processor count.

        Args:
            count (int): Number of processors.
        """
        self.count = count

    def get_logical_processor_count(self) -> int:
        """Get logical processor count.

        Returns:
            int: Number of logical processors.
        """
        return self.logical_processor_count

    def set_logical_processor_count(self, logical_processor_count: int) -> None:
        """Set logical processor count.

        Args:
            logical_processor_count (int): Number of logical processors.
        """
        self.logical_processor_count = logical_processor_count

    def get_model(self) -> str:
        """Get processor model.

        Returns:
            str: Processor model name.
        """
        return self.model

    def set_model(self, model: str) -> None:
        """Set processor model.

        Args:
            model (str): Processor model name.
        """
        self.model = model

    def get_threading_enabled(self) -> bool:
        """Get threading enabled status.

        Returns:
            bool: Whether threading is enabled.
        """
        return self.threading_enabled

    def set_threading_enabled(self, threading_enabled: bool) -> None:
        """Set threading enabled status.

        Args:
            threading_enabled (bool): Whether threading is enabled.
        """
        self.threading_enabled = threading_enabled

    def get_status(self) -> Status:
        """Get processor status.

        Returns:
            Status: Processor status object.
        """
        return self.status

    def set_status(self, status: Status) -> None:
        """Set processor status.

        Args:
            status (Status): Processor status object.
        """
        self.status = status
