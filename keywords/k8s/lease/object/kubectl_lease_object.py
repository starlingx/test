"""Object representing a Kubernetes Lease resource."""


class KubectlLeaseObject:
    """Object representing a Kubernetes Lease."""

    def __init__(self, name: str):
        """Initialize Lease object.

        Args:
            name (str): Name of the lease.
        """
        self._name = name
        self._holder = None
        self._age = None

    def get_name(self) -> str:
        """Get lease name.

        Returns:
            str: Lease name.
        """
        return self._name

    def get_holder(self) -> str:
        """Get lease holder.

        Returns:
            str: Lease holder identity.
        """
        return self._holder

    def set_holder(self, holder: str) -> None:
        """Set lease holder.

        Args:
            holder (str): Lease holder identity.
        """
        self._holder = holder

    def get_age(self) -> str:
        """Get lease age.

        Returns:
            str: Lease age.
        """
        return self._age

    def set_age(self, age: str) -> None:
        """Set lease age.

        Args:
            age (str): Lease age.
        """
        self._age = age
