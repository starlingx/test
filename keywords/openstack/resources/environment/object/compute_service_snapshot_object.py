"""Compute service snapshot object."""


class ComputeServiceSnapshotObject:
    """Represents a Nova compute service state in a snapshot."""

    def __init__(self):
        """Initialize ComputeServiceSnapshotObject."""
        self._host = ""
        self._state = ""
        self._status = ""

    def get_host(self) -> str:
        """Get the host name.

        Returns:
            str: Host name.
        """
        return self._host

    def set_host(self, host: str) -> None:
        """Set the host name.

        Args:
            host (str): Host name.
        """
        self._host = host

    def get_state(self) -> str:
        """Get the service state.

        Returns:
            str: Service state (e.g. 'up', 'down').
        """
        return self._state

    def set_state(self, state: str) -> None:
        """Set the service state.

        Args:
            state (str): Service state.
        """
        self._state = state

    def get_status(self) -> str:
        """Get the service status.

        Returns:
            str: Service status (e.g. 'enabled', 'disabled').
        """
        return self._status

    def set_status(self, status: str) -> None:
        """Set the service status.

        Args:
            status (str): Service status.
        """
        self._status = status
