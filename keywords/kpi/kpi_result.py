"""KPI Result data class for structured KPI timing data."""


class KpiResult:
    """Represents a single parsed KPI timing result."""

    def __init__(self, label: str, duration_seconds: float, hostname: str):
        """
        Initialize KpiResult.

        Args:
            label (str): Phase label (e.g., "SHUTDOWN PHASE").
            duration_seconds (float): Duration in seconds.
            hostname (str): Hostname of the target host.
        """
        self.label = label
        self.duration_seconds = duration_seconds
        self.hostname = hostname

    def get_label(self) -> str:
        """Get the phase label."""
        return self.label

    def get_duration_seconds(self) -> float:
        """Get the duration in seconds."""
        return self.duration_seconds

    def get_hostname(self) -> str:
        """Get the hostname."""
        return self.hostname

    def __repr__(self) -> str:
        return (f"KpiResult(label='{self.label}', "
                f"duration_seconds={self.duration_seconds}, "
                f"hostname='{self.hostname}')")
