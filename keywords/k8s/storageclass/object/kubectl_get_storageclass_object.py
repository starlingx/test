"""Kubernetes StorageClass object representation."""

from typing import Dict, Optional


class KubectlGetStorageclassObject:
    """Represents a single Kubernetes StorageClass resource.

    Stores parsed data from 'kubectl get sc -o yaml' for a single
    StorageClass entry, including classification metadata for
    storage type detection.
    """

    def __init__(self, name: str) -> None:
        """Initialize StorageClass object.

        Args:
            name (str): Name of the StorageClass.
        """
        self.name = name
        self.provisioner = None
        self.reclaim_policy = None
        self.volume_binding_mode = None
        self.allow_volume_expansion = None
        self.parameters = None
        self.is_default = False
        self.storage_type = None

    def get_name(self) -> str:
        """Get the StorageClass name.

        Returns:
            str: The name of the StorageClass.
        """
        return self.name

    def get_provisioner(self) -> Optional[str]:
        """Get the provisioner.

        Returns:
            Optional[str]: The provisioner string.
        """
        return self.provisioner

    def set_provisioner(self, provisioner: str) -> None:
        """Set the provisioner.

        Args:
            provisioner (str): The provisioner string.
        """
        self.provisioner = provisioner

    def get_reclaim_policy(self) -> Optional[str]:
        """Get the reclaim policy.

        Returns:
            Optional[str]: The reclaim policy.
        """
        return self.reclaim_policy

    def set_reclaim_policy(self, reclaim_policy: str) -> None:
        """Set the reclaim policy.

        Args:
            reclaim_policy (str): The reclaim policy.
        """
        self.reclaim_policy = reclaim_policy

    def get_volume_binding_mode(self) -> Optional[str]:
        """Get the volume binding mode.

        Returns:
            Optional[str]: The volume binding mode.
        """
        return self.volume_binding_mode

    def set_volume_binding_mode(self, volume_binding_mode: str) -> None:
        """Set the volume binding mode.

        Args:
            volume_binding_mode (str): The volume binding mode.
        """
        self.volume_binding_mode = volume_binding_mode

    def get_allow_volume_expansion(self) -> Optional[bool]:
        """Get whether volume expansion is allowed.

        Returns:
            Optional[bool]: True if volume expansion is allowed.
        """
        return self.allow_volume_expansion

    def set_allow_volume_expansion(self, allow_volume_expansion: bool) -> None:
        """Set whether volume expansion is allowed.

        Args:
            allow_volume_expansion (bool): True if volume expansion is allowed.
        """
        self.allow_volume_expansion = allow_volume_expansion

    def get_parameters(self) -> Optional[Dict]:
        """Get the StorageClass parameters.

        Returns:
            Optional[Dict]: The parameters dictionary.
        """
        return self.parameters

    def set_parameters(self, parameters: Dict) -> None:
        """Set the StorageClass parameters.

        Args:
            parameters (Dict): The parameters dictionary.
        """
        self.parameters = parameters

    def get_is_default(self) -> bool:
        """Get whether this is the default StorageClass.

        Returns:
            bool: True if this is the default StorageClass.
        """
        return self.is_default

    def set_is_default(self, is_default: bool) -> None:
        """Set whether this is the default StorageClass.

        Args:
            is_default (bool): True if this is the default StorageClass.
        """
        self.is_default = is_default

    def get_storage_type(self) -> Optional[str]:
        """Get the classified storage type.

        Returns:
            Optional[str]: The storage type (e.g., 'ceph-rbd', 'cephfs',
                'netapp-iscsi', 'netapp-fc', 'netapp-nfs', 'unknown').
        """
        return self.storage_type

    def set_storage_type(self, storage_type: str) -> None:
        """Set the classified storage type.

        Args:
            storage_type (str): The storage type.
        """
        self.storage_type = storage_type

    def __str__(self) -> str:
        """Get string representation for logging.

        Returns:
            str: Human-readable representation of the StorageClass.
        """
        return f"StorageClass(name={self.name}, provisioner={self.provisioner}, " f"type={self.storage_type}, default={self.is_default})"
