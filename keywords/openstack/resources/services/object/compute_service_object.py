"""Compute service object representation."""


class ComputeServiceObject:
    """Represents a single Nova compute service."""

    def __init__(self) -> None:
        """Initialize an empty ComputeServiceObject."""
        self._binary = ""
        self._host = ""
        self._zone = ""
        self._status = ""
        self._state = ""
        self._updated_at = ""

    def get_binary(self) -> str:
        """Get the service binary name.

        Returns:
            str: Service binary (e.g. 'nova-compute', 'nova-scheduler').
        """
        return self._binary

    def set_binary(self, binary: str) -> None:
        """Set the service binary name.

        Args:
            binary (str): Service binary name.
        """
        self._binary = binary

    def get_host(self) -> str:
        """Get the service host.

        Returns:
            str: Host name (e.g. 'controller-0', 'compute-0').
        """
        return self._host

    def set_host(self, host: str) -> None:
        """Set the service host.

        Args:
            host (str): Host name.
        """
        self._host = host

    def get_zone(self) -> str:
        """Get the availability zone.

        Returns:
            str: Availability zone (e.g. 'nova').
        """
        return self._zone

    def set_zone(self, zone: str) -> None:
        """Set the availability zone.

        Args:
            zone (str): Availability zone.
        """
        self._zone = zone

    def get_status(self) -> str:
        """Get the service admin status.

        Returns:
            str: Admin status (e.g. 'enabled', 'disabled').
        """
        return self._status

    def set_status(self, status: str) -> None:
        """Set the service admin status.

        Args:
            status (str): Admin status.
        """
        self._status = status

    def get_state(self) -> str:
        """Get the service runtime state.

        Returns:
            str: Runtime state (e.g. 'up', 'down').
        """
        return self._state

    def set_state(self, state: str) -> None:
        """Set the service runtime state.

        Args:
            state (str): Runtime state.
        """
        self._state = state

    def get_updated_at(self) -> str:
        """Get the last updated timestamp.

        Returns:
            str: Last updated timestamp string.
        """
        return self._updated_at

    def set_updated_at(self, updated_at: str) -> None:
        """Set the last updated timestamp.

        Args:
            updated_at (str): Last updated timestamp string.
        """
        self._updated_at = updated_at

    def is_up(self) -> bool:
        """Check if the service is up and enabled.

        Returns:
            bool: True if state is 'up' and status is 'enabled'.
        """
        return self._state == "up" and self._status == "enabled"

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable representation.
        """
        return (
            f"ComputeServiceObject(binary={self._binary}, host={self._host}, "
            f"status={self._status}, state={self._state})"
        )
