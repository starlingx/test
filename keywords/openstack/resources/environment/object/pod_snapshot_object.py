"""Pod snapshot object."""


class PodSnapshotObject:
    """Represents an OpenStack pod state in a snapshot."""

    def __init__(self):
        """Initialize PodSnapshotObject."""
        self._name = ""
        self._status = ""

    def get_name(self) -> str:
        """Get the pod name.

        Returns:
            str: Pod name.
        """
        return self._name

    def set_name(self, name: str) -> None:
        """Set the pod name.

        Args:
            name (str): Pod name.
        """
        self._name = name

    def get_status(self) -> str:
        """Get the pod status.

        Returns:
            str: Pod status (e.g. 'Running', 'Completed').
        """
        return self._status

    def set_status(self, status: str) -> None:
        """Set the pod status.

        Args:
            status (str): Pod status.
        """
        self._status = status
