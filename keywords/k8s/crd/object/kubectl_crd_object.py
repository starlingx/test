"""Object representing a Kubernetes CRD resource."""

from typing import Optional


class KubectlCrdObject:
    """Object representing a Kubernetes Custom Resource Definition."""

    def __init__(self, name: str):
        """Initialize CRD object.

        Args:
            name (str): Name of the CRD.
        """
        self._name = name
        self._created_at = None
        self._group = self._extract_group(name)
        self._established = None

    @staticmethod
    def _extract_group(name: str) -> str:
        """Extract the API group from the CRD name.

        Args:
            name (str): Full CRD name (e.g. 'prometheuses.monitoring.coreos.com').

        Returns:
            str: The API group (e.g. 'monitoring.coreos.com').
        """
        parts = name.split(".", 1)
        return parts[1] if len(parts) > 1 else ""

    def get_name(self) -> str:
        """Get CRD name.

        Returns:
            str: CRD name (e.g. 'ovsbridges.openvswitch.starlingx.io').
        """
        return self._name

    def get_group(self) -> str:
        """Get the API group of the CRD.

        Returns:
            str: The API group (e.g. 'monitoring.coreos.com').
        """
        return self._group

    def set_created_at(self, created_at: str) -> None:
        """Set CRD creation timestamp.

        Args:
            created_at (str): Creation timestamp.
        """
        self._created_at = created_at

    def get_created_at(self) -> Optional[str]:
        """Get CRD creation timestamp.

        Returns:
            Optional[str]: Creation timestamp, or None if not set.
        """
        return self._created_at

    def set_established(self, established: bool) -> None:
        """Set whether the CRD is in Established condition.

        Args:
            established (bool): True if the CRD is established.
        """
        self._established = established

    def get_established(self) -> Optional[bool]:
        """Get whether the CRD is in Established condition.

        Returns:
            Optional[bool]: True if established, None if not checked.
        """
        return self._established

    def __str__(self) -> str:
        """Human-readable string representation.

        Returns:
            str: CRD name and group.
        """
        return f"CRD(name={self._name}, group={self._group})"
