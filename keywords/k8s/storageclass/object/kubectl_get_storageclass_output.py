"""Kubernetes StorageClass output parser."""

from typing import Dict, List, Optional, Union

import yaml

from keywords.k8s.storageclass.object.kubectl_get_storageclass_object import KubectlGetStorageclassObject


class KubectlGetStorageclassOutput:
    """Parses and manages a collection of Kubernetes StorageClass resources.

    Parses YAML output from 'kubectl get sc -o yaml' and provides
    methods for querying and classifying storage backends.
    """

    DEFAULT_ANNOTATION = "storageclass.kubernetes.io/is-default-class"

    def __init__(self, kubectl_get_sc_output: Union[str, List[str]]) -> None:
        """Create StorageClass collection from kubectl YAML output.

        Args:
            kubectl_get_sc_output (Union[str, List[str]]): Raw YAML output
                from 'kubectl get sc -o yaml'.
        """
        self.storageclasses: List[KubectlGetStorageclassObject] = []

        if isinstance(kubectl_get_sc_output, list):
            kubectl_get_sc_output = "\n".join(kubectl_get_sc_output)

        parsed = yaml.safe_load(kubectl_get_sc_output)

        if not parsed or "items" not in parsed:
            return

        for item in parsed["items"]:
            metadata = item.get("metadata", {})
            name = metadata.get("name")

            if not name:
                raise ValueError(f"StorageClass has no name: {item}")

            sc_object = KubectlGetStorageclassObject(name)

            sc_object.set_provisioner(item.get("provisioner", ""))
            sc_object.set_reclaim_policy(item.get("reclaimPolicy"))
            sc_object.set_volume_binding_mode(item.get("volumeBindingMode"))
            sc_object.set_allow_volume_expansion(item.get("allowVolumeExpansion", False))
            sc_object.set_parameters(item.get("parameters", {}))

            annotations = metadata.get("annotations", {})
            is_default = annotations.get(self.DEFAULT_ANNOTATION, "false").lower() == "true"
            sc_object.set_is_default(is_default)

            storage_type = self._classify_storage_type(
                sc_object.get_provisioner(),
                sc_object.get_parameters(),
            )
            sc_object.set_storage_type(storage_type)

            self.storageclasses.append(sc_object)

    def _classify_storage_type(self, provisioner: str, parameters: Dict) -> str:
        """Classify storage type based on provisioner and parameters.

        Classification rules:
        - cephfs: provisioner contains 'cephfs'
        - ceph-rbd: provisioner contains 'rbd' or 'ceph'
        - netapp-iscsi: provisioner contains 'trident'/'netapp' + ontap-san + iscsi
        - netapp-fc: provisioner contains 'trident'/'netapp' + ontap-san + fc
        - netapp-nfs: provisioner contains 'trident'/'netapp' + ontap-nas

        Note: 'cephfs' must be checked before 'ceph'/'rbd' because the cephfs
        provisioner (rook-ceph.cephfs.csi.ceph.com) contains both 'cephfs' and 'ceph'.

        Args:
            provisioner (str): The StorageClass provisioner string.
            parameters (Dict): The StorageClass parameters dictionary.

        Returns:
            str: The classified storage type.
        """
        provisioner_lower = provisioner.lower()
        backend_type = parameters.get("backendType", "")
        san_type = parameters.get("sanType", "")

        if "cephfs" in provisioner_lower:
            return "cephfs"
        if "rbd" in provisioner_lower or "ceph" in provisioner_lower:
            return "ceph-rbd"
        if "trident" in provisioner_lower or "netapp" in provisioner_lower:
            if backend_type == "ontap-nas":
                return "netapp-nfs"
            if backend_type == "ontap-san":
                if san_type == "fc":
                    return "netapp-fc"
                return "netapp-iscsi"
        return "unknown"

    def get_storageclasses(self) -> List[KubectlGetStorageclassObject]:
        """Get all StorageClass objects.

        Returns:
            List[KubectlGetStorageclassObject]: List of all StorageClass objects.
        """
        return self.storageclasses

    def get_storageclass_by_name(self, name: str) -> KubectlGetStorageclassObject:
        """Get a StorageClass by name.

        Args:
            name (str): The name of the StorageClass.

        Returns:
            KubectlGetStorageclassObject: The StorageClass object.

        Raises:
            ValueError: If no StorageClass with the given name exists.
        """
        for sc in self.storageclasses:
            if sc.get_name() == name:
                return sc
        raise ValueError(f"No StorageClass with name '{name}' found.")

    def get_default_storageclass(self) -> Optional[KubectlGetStorageclassObject]:
        """Get the default StorageClass.

        Returns:
            Optional[KubectlGetStorageclassObject]: The default StorageClass,
                or None if no default is set.
        """
        for sc in self.storageclasses:
            if sc.get_is_default():
                return sc
        return None

    def get_available_storage_types(self) -> List[str]:
        """Get all unique storage types detected in the cluster.

        Returns:
            List[str]: Sorted list of unique storage types.
        """
        return sorted({sc.get_storage_type() for sc in self.storageclasses if sc.get_storage_type()})

    def get_available_sans(self) -> List[str]:
        """Get available SAN storage types.

        Returns:
            List[str]: List of detected SAN types (ceph-rbd, netapp-iscsi, netapp-fc).
        """
        san_types = {"ceph-rbd", "netapp-iscsi", "netapp-fc"}
        return sorted(san_types & set(self.get_available_storage_types()))

    def get_available_nas(self) -> List[str]:
        """Get available NAS storage types.

        Returns:
            List[str]: List of detected NAS types (cephfs, netapp-nfs).
        """
        nas_types = {"cephfs", "netapp-nfs"}
        return sorted(nas_types & set(self.get_available_storage_types()))

    def has_storage_type(self, storage_type: str) -> bool:
        """Check if a specific storage type is available.

        Args:
            storage_type (str): The storage type to check.

        Returns:
            bool: True if the storage type is available.
        """
        return storage_type in self.get_available_storage_types()

    def __str__(self) -> str:
        """Get string representation for logging.

        Returns:
            str: Human-readable summary of the StorageClass collection.
        """
        return f"KubectlGetStorageclassOutput(count={len(self.storageclasses)}, types={self.get_available_storage_types()})"
