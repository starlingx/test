"""Keywords for determining and validating storage capabilities.

Uses existing KubectlGetStorageclassKeywords for StorageClass detection
and KubectlGetTridentBackendConfigKeywords for NetApp backend health validation.

Capabilities:
    - general (ceph-rbd): Ceph RBD (rook-ceph.rbd.csi.ceph.com)
    - cephfs: CephFS (rook-ceph.cephfs.csi.ceph.com)
    - netapp-nfs: NetApp ONTAP NAS (csi.trident.netapp.io + ontap-nas)
    - netapp-iscsi: NetApp ONTAP SAN iSCSI (csi.trident.netapp.io + ontap-san)
    - netapp-fc: NetApp ONTAP SAN FC (csi.trident.netapp.io + ontap-san-fc)
"""

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.storageclass.kubectl_get_storageclass_keywords import KubectlGetStorageclassKeywords
from keywords.k8s.trident.kubectl_get_trident_backend_config_keywords import KubectlGetTridentBackendConfigKeywords


# Mapping from storage type (as classified by KubectlGetStorageclassOutput) to TBC driver
_STORAGE_TYPE_TO_DRIVER = {
    "netapp-nfs": "ontap-nas",
    "netapp-iscsi": "ontap-san",
    "netapp-fc": "ontap-san-fc",
}


class StorageCapabilityKeywords:
    """Keywords for determining and validating storage capabilities."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize StorageCapabilityKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
        """
        self._ssh_connection = ssh_connection
        self._kubeconfig_path = kubeconfig_path

    def determine_capability(self, storage_class_name: str) -> str:
        """Determine the storage capability from a StorageClass name.

        Uses existing KubectlGetStorageclassKeywords to get the StorageClass
        and its classified storage_type.

        Args:
            storage_class_name (str): Name of the StorageClass.

        Returns:
            str: One of 'ceph-rbd', 'cephfs', 'netapp-nfs', 'netapp-iscsi',
                'netapp-fc', or 'unknown' if the provisioner is not recognized.

        Raises:
            KeywordException: If the StorageClass is not found.
        """
        sc_kw = KubectlGetStorageclassKeywords(self._ssh_connection, self._kubeconfig_path)
        sc_output = sc_kw.get_storageclasses()
        sc = sc_output.get_storageclass_by_name(storage_class_name)
        storage_type = sc.get_storage_type()

        if storage_type == "unknown":
            get_logger().log_warning(
                f"StorageClass '{storage_class_name}' has unrecognized provisioner: "
                f"{sc.get_provisioner()}"
            )
        else:
            get_logger().log_info(
                f"StorageClass '{storage_class_name}': capability={storage_type}"
            )
        return storage_type

    def determine_backend_family(self, storage_class_name: str) -> str:
        """Determine the backend family from a StorageClass.

        Args:
            storage_class_name (str): Name of the StorageClass.

        Returns:
            str: One of 'ceph', 'netapp', or 'unknown'.
        """
        capability = self.determine_capability(storage_class_name)
        if capability in ("ceph-rbd", "cephfs"):
            return "ceph"
        if capability.startswith("netapp-"):
            return "netapp"
        return "unknown"

    def assert_netapp_backend_available(self, required_capability: str) -> None:
        """Verify that a healthy NetApp backend exists for the required capability.

        Queries TridentBackendConfig resources and checks that at least one
        backend with the matching storageDriverName has lastOperationStatus == Success.

        Args:
            required_capability (str): One of 'netapp-nfs', 'netapp-iscsi', 'netapp-fc'.

        Raises:
            KeywordException: If no healthy backend is found for the capability.
        """
        if required_capability not in _STORAGE_TYPE_TO_DRIVER:
            raise KeywordException(
                f"'{required_capability}' is not a NetApp capability. "
                f"Valid values: {list(_STORAGE_TYPE_TO_DRIVER.keys())}"
            )

        required_driver = _STORAGE_TYPE_TO_DRIVER[required_capability]
        get_logger().log_info(
            f"Verifying NetApp backend for capability '{required_capability}' "
            f"(driver: {required_driver})"
        )

        tbc_kw = KubectlGetTridentBackendConfigKeywords(self._ssh_connection, self._kubeconfig_path)
        tbc_output = tbc_kw.get_trident_backend_configs()

        if tbc_output.has_healthy_backend_for_driver(required_driver):
            healthy = tbc_output.get_healthy_configs_by_driver(required_driver)
            get_logger().log_info(
                f"Healthy NetApp backend found: {healthy[0].get_name()} "
                f"(driver={required_driver}, status=Success)"
            )
            return

        # Log all backends for debugging
        all_for_driver = tbc_output.get_configs_by_driver(required_driver)
        if all_for_driver:
            for tbc in all_for_driver:
                get_logger().log_info(
                    f"  TBC '{tbc.get_name()}': driver={tbc.get_storage_driver_name()}, "
                    f"status={tbc.get_last_operation_status()}, msg={tbc.get_message()}"
                )

        raise KeywordException(
            f"No healthy NetApp backend for capability '{required_capability}'. "
            f"Required driver '{required_driver}' has no TBC with lastOperationStatus=Success."
        )

    def determine_capability_and_assert_backend(self, storage_class_name: str) -> str:
        """Determine capability from StorageClass and assert NetApp backend health.

        This is the main entry point for tests. It:
        1. Determines the capability from the StorageClass
        2. For NetApp capabilities, asserts a healthy TridentBackendConfig exists
        3. For Ceph capabilities, returns the capability without additional checks
           (Ceph health is managed by rook-ceph operator)

        Args:
            storage_class_name (str): Name of the StorageClass.

        Returns:
            str: The capability string (e.g. 'ceph-rbd', 'netapp-nfs').

        Raises:
            KeywordException: If capability is unknown or
                NetApp backend is unavailable.
        """
        capability = self.determine_capability(storage_class_name)

        if capability == "unknown":
            raise KeywordException(
                f"Cannot determine capability for StorageClass '{storage_class_name}'"
            )

        if capability.startswith("netapp-"):
            self.assert_netapp_backend_available(capability)

        return capability
