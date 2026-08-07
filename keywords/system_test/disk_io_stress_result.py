"""Object representing the result of a disk I/O stress generation run."""


class DiskIOStressResult:
    """Holds the outcome of a disk I/O stress generation operation."""

    def __init__(self) -> None:
        """Constructor."""
        self.start_timestamp = ""
        self.end_timestamp = ""
        self.hostname = ""

    def set_start_timestamp(self, start_timestamp: str) -> None:
        """Set the ISO 8601 UTC timestamp when stress started.

        Args:
            start_timestamp (str): Start timestamp in ISO 8601 format.
        """
        self.start_timestamp = start_timestamp

    def get_start_timestamp(self) -> str:
        """Get the ISO 8601 UTC timestamp when stress started.

        Returns:
            str: Start timestamp in ISO 8601 format.
        """
        return self.start_timestamp

    def set_end_timestamp(self, end_timestamp: str) -> None:
        """Set the ISO 8601 UTC timestamp when stress ended.

        Args:
            end_timestamp (str): End timestamp in ISO 8601 format.
        """
        self.end_timestamp = end_timestamp

    def get_end_timestamp(self) -> str:
        """Get the ISO 8601 UTC timestamp when stress ended.

        Returns:
            str: End timestamp in ISO 8601 format.
        """
        return self.end_timestamp

    def set_hostname(self, hostname: str) -> None:
        """Set the hostname where stress was generated.

        Args:
            hostname (str): Target hostname.
        """
        self.hostname = hostname

    def get_hostname(self) -> str:
        """Get the hostname where stress was generated.

        Returns:
            str: Target hostname.
        """
        return self.hostname

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: String summary of the stress result.
        """
        return f"DiskIOStressResult(host={self.hostname}, start={self.start_timestamp}, end={self.end_timestamp})"
