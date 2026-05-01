"""Kubectl PV Object for representing a Kubernetes PersistentVolume."""


class KubectlPvObject:
    """Represents a single Kubernetes PersistentVolume from kubectl get pv output."""

    def __init__(self, name: str):
        """Constructor.

        Args:
            name (str): Name of the PersistentVolume.
        """
        self._properties = {"name": name}

    def get_name(self) -> str:
        """Get the PV name.

        Returns:
            str: The PV name.
        """
        return self._properties.get("name")

    def set_capacity(self, capacity: str) -> None:
        """Set the PV capacity.

        Args:
            capacity (str): Capacity value (e.g., '10Gi').
        """
        self._properties["capacity"] = capacity

    def get_capacity(self) -> str:
        """Get the PV capacity.

        Returns:
            str: The PV capacity.
        """
        return self._properties.get("capacity")

    def set_access_modes(self, access_modes: str) -> None:
        """Set the PV access modes.

        Args:
            access_modes (str): Access modes (e.g., 'RWO').
        """
        self._properties["access_modes"] = access_modes

    def get_access_modes(self) -> str:
        """Get the PV access modes.

        Returns:
            str: The PV access modes.
        """
        return self._properties.get("access_modes")

    def set_reclaim_policy(self, reclaim_policy: str) -> None:
        """Set the PV reclaim policy.

        Args:
            reclaim_policy (str): Reclaim policy (e.g., 'Retain', 'Delete').
        """
        self._properties["reclaim_policy"] = reclaim_policy

    def get_reclaim_policy(self) -> str:
        """Get the PV reclaim policy.

        Returns:
            str: The PV reclaim policy.
        """
        return self._properties.get("reclaim_policy")

    def set_status(self, status: str) -> None:
        """Set the PV status.

        Args:
            status (str): Status value (e.g., 'Bound', 'Available', 'Released').
        """
        self._properties["status"] = status

    def get_status(self) -> str:
        """Get the PV status.

        Returns:
            str: The PV status.
        """
        return self._properties.get("status")

    def set_claim(self, claim: str) -> None:
        """Set the PV claim.

        Args:
            claim (str): Claim reference (e.g., 'monitor/data-elasticsearch-0').
        """
        self._properties["claim"] = claim

    def get_claim(self) -> str:
        """Get the PV claim.

        Returns:
            str: The PV claim reference.
        """
        return self._properties.get("claim")

    def set_storageclass(self, storageclass: str) -> None:
        """Set the PV storage class.

        Args:
            storageclass (str): Storage class name.
        """
        self._properties["storageclass"] = storageclass

    def get_storageclass(self) -> str:
        """Get the PV storage class.

        Returns:
            str: The PV storage class.
        """
        return self._properties.get("storageclass")

    def set_reason(self, reason: str) -> None:
        """Set the PV reason.

        Args:
            reason (str): Reason value.
        """
        self._properties["reason"] = reason

    def get_reason(self) -> str:
        """Get the PV reason.

        Returns:
            str: The PV reason.
        """
        return self._properties.get("reason")

    def set_age(self, age: str) -> None:
        """Set the PV age.

        Args:
            age (str): Age value (e.g., '5d').
        """
        self._properties["age"] = age

    def get_age(self) -> str:
        """Get the PV age.

        Returns:
            str: The PV age.
        """
        return self._properties.get("age")

    def set_volumemode(self, volumemode: str) -> None:
        """Set the PV volume mode.

        Args:
            volumemode (str): Volume mode (e.g., 'Filesystem', 'Block').
        """
        self._properties["volumemode"] = volumemode

    def get_volumemode(self) -> str:
        """Get the PV volume mode.

        Returns:
            str: The PV volume mode.
        """
        return self._properties.get("volumemode")

    def is_bound(self) -> bool:
        """Check if the PV is in Bound status.

        Returns:
            bool: True if the PV status is 'Bound'.
        """
        return self.get_status() == "Bound"

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: PV name, status, and claim.
        """
        return f"PV(name={self.get_name()}, status={self.get_status()}, claim={self.get_claim()})"
