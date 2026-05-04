"""Kubernetes PersistentVolumeClaim object representation."""

from typing import Optional


class KubectlPvcObject:
    """Represents a single Kubernetes PersistentVolumeClaim resource.

    Stores parsed data from 'kubectl get pvc -o wide' for a single
    PVC entry.
    """

    def __init__(self, name: str) -> None:
        """Initialize PVC object.

        Args:
            name (str): Name of the PVC.
        """
        self.name = name
        self.namespace = None
        self.status = None
        self.volume = None
        self.capacity = None
        self.access_modes = None
        self.storageclass = None
        self.volumeattributesclass = None
        self.age = None
        self.volumemode = None

    def get_name(self) -> str:
        """Get the PVC name.

        Returns:
            str: The name of the PVC.
        """
        return self.name

    def get_namespace(self) -> Optional[str]:
        """Get the namespace.

        Returns:
            Optional[str]: The namespace.
        """
        return self.namespace

    def set_namespace(self, namespace: str) -> None:
        """Set the namespace.

        Args:
            namespace (str): The namespace.
        """
        self.namespace = namespace

    def get_status(self) -> Optional[str]:
        """Get the PVC status.

        Returns:
            Optional[str]: The status (e.g., 'Bound', 'Pending').
        """
        return self.status

    def set_status(self, status: str) -> None:
        """Set the PVC status.

        Args:
            status (str): The status.
        """
        self.status = status

    def get_volume(self) -> Optional[str]:
        """Get the bound PersistentVolume name.

        Returns:
            Optional[str]: The PV name.
        """
        return self.volume

    def set_volume(self, volume: str) -> None:
        """Set the bound PersistentVolume name.

        Args:
            volume (str): The PV name.
        """
        self.volume = volume

    def get_capacity(self) -> Optional[str]:
        """Get the storage capacity.

        Returns:
            Optional[str]: The capacity (e.g., '5Gi').
        """
        return self.capacity

    def set_capacity(self, capacity: str) -> None:
        """Set the storage capacity.

        Args:
            capacity (str): The capacity.
        """
        self.capacity = capacity

    def get_access_modes(self) -> Optional[str]:
        """Get the access modes.

        Returns:
            Optional[str]: The access modes (e.g., 'RWO').
        """
        return self.access_modes

    def set_access_modes(self, access_modes: str) -> None:
        """Set the access modes.

        Args:
            access_modes (str): The access modes.
        """
        self.access_modes = access_modes

    def get_storageclass(self) -> Optional[str]:
        """Get the StorageClass name.

        Returns:
            Optional[str]: The StorageClass name.
        """
        return self.storageclass

    def set_storageclass(self, storageclass: str) -> None:
        """Set the StorageClass name.

        Args:
            storageclass (str): The StorageClass name.
        """
        self.storageclass = storageclass

    def get_volumeattributesclass(self) -> Optional[str]:
        """Get the volume attributes class.

        Returns:
            Optional[str]: The volume attributes class.
        """
        return self.volumeattributesclass

    def set_volumeattributesclass(self, volumeattributesclass: str) -> None:
        """Set the volume attributes class.

        Args:
            volumeattributesclass (str): The volume attributes class.
        """
        self.volumeattributesclass = volumeattributesclass

    def get_age(self) -> Optional[str]:
        """Get the age.

        Returns:
            Optional[str]: The age.
        """
        return self.age

    def set_age(self, age: str) -> None:
        """Set the age.

        Args:
            age (str): The age.
        """
        self.age = age

    def get_volumemode(self) -> Optional[str]:
        """Get the volume mode.

        Returns:
            Optional[str]: The volume mode (e.g., 'Filesystem').
        """
        return self.volumemode

    def set_volumemode(self, volumemode: str) -> None:
        """Set the volume mode.

        Args:
            volumemode (str): The volume mode.
        """
        self.volumemode = volumemode

    def __str__(self) -> str:
        """Get string representation for logging.

        Returns:
            str: Human-readable representation of the PVC.
        """
        return (
            f"PVC(name={self.name}, namespace={self.namespace}, "
            f"status={self.status}, storageclass={self.storageclass}, "
            f"capacity={self.capacity})"
        )

    def __repr__(self) -> str:
        """Get repr for debugging.

        Returns:
            str: Same as __str__.
        """
        return self.__str__()
