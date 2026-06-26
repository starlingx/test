"""Object representing a Kubernetes CRD resource."""


class KubectlCrdObject:
    """Object representing a Kubernetes Custom Resource Definition."""

    def __init__(self, name: str):
        """Initialize CRD object.

        Args:
            name (str): Name of the CRD.
        """
        self._name = name
        self._created_at = None

    def get_name(self) -> str:
        """Get CRD name.

        Returns:
            str: CRD name (e.g. 'ovsbridges.openvswitch.starlingx.io').
        """
        return self._name

    def set_created_at(self, created_at: str) -> None:
        """Set CRD creation timestamp.

        Args:
            created_at (str): Creation timestamp.
        """
        self._created_at = created_at

    def get_created_at(self) -> str:
        """Get CRD creation timestamp.

        Returns:
            str: Creation timestamp.
        """
        return self._created_at
