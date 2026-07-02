"""Hypervisor snapshot object."""


class HypervisorSnapshotObject:
    """Represents a hypervisor state in a snapshot."""

    def __init__(self):
        """Initialize HypervisorSnapshotObject."""
        self._name = ""
        self._state = ""
        self._status = ""

    def get_name(self) -> str:
        """Get the hypervisor name.

        Returns:
            str: Hypervisor name.
        """
        return self._name

    def set_name(self, name: str) -> None:
        """Set the hypervisor name.

        Args:
            name (str): Hypervisor name.
        """
        self._name = name

    def get_state(self) -> str:
        """Get the hypervisor state.

        Returns:
            str: Hypervisor state (e.g. 'up', 'down').
        """
        return self._state

    def set_state(self, state: str) -> None:
        """Set the hypervisor state.

        Args:
            state (str): Hypervisor state.
        """
        self._state = state

    def get_status(self) -> str:
        """Get the hypervisor status.

        Returns:
            str: Hypervisor status (e.g. 'enabled', 'disabled').
        """
        return self._status

    def set_status(self, status: str) -> None:
        """Set the hypervisor status.

        Args:
            status (str): Hypervisor status.
        """
        self._status = status
