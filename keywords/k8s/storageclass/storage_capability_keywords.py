"""Keywords for determining and validating storage capabilities.

Uses existing KubectlGetStorageclassKeywords for StorageClass detection
and KubectlGetTridentBackendConfigKeywords for NetApp backend health validation.

Capabilities:
    - general (ceph-rbd): Ceph RBD (rook-ceph.rbd.csi.ceph.com)
    - cephfs: CephFS (rook-ceph.cephfs.csi.ceph.com)
    - netapp-nfs: NetApp ONTAP NAS (ontap-nas)
    - netapp-iscsi: NetApp ONTAP SAN iSCSI (ontap-san + sanType iscsi)
    - netapp-fc: NetApp ONTAP SAN Fibre Channel (ontap-san + sanType fcp)

A NetApp SAN StorageClass only carries 'backendType: ontap-san', which the
netapp-storage chart uses for iSCSI, Fibre Channel and NVMe alike, so the
StorageClass cannot name the protocol on its own. The protocol comes from the
sanType of the TridentBackendConfig, and resolving the two together is what
this module does.
"""

from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.storageclass.kubectl_get_storageclass_keywords import KubectlGetStorageclassKeywords
from keywords.k8s.storageclass.object.kubectl_get_storageclass_object import KubectlGetStorageclassObject
from keywords.k8s.trident.kubectl_get_trident_backend_config_keywords import KubectlGetTridentBackendConfigKeywords
from keywords.k8s.trident.object.kubectl_get_trident_backend_config_output import KubectlGetTridentBackendConfigOutput
from keywords.k8s.trident.object.kubectl_trident_backend_config_object import KubectlTridentBackendConfigObject

# Mapping from NetApp capability to the TBC storage driver and, for the SAN
# protocols that share the ontap-san driver, the sanType that identifies it.
_NETAPP_CAPABILITY_TO_BACKEND = {
    "netapp-nfs": ("ontap-nas", None),
    "netapp-iscsi": ("ontap-san", "iscsi"),
    "netapp-fc": ("ontap-san", "fcp"),
}

# Storage type reported for any NetApp SAN StorageClass, which cannot tell the
# SAN protocols apart on its own.
_NETAPP_SAN_STORAGE_TYPE = "netapp-san"


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

        Uses existing KubectlGetStorageclassKeywords to get the StorageClass and
        its classified storage_type. A NetApp SAN StorageClass does not name its
        protocol, so for those the sanType of the healthy TridentBackendConfig
        decides between iSCSI and Fibre Channel.

        Args:
            storage_class_name (str): Name of the StorageClass.

        Returns:
            str: One of 'ceph-rbd', 'cephfs', 'netapp-nfs', 'netapp-iscsi',
                'netapp-fc', or 'unknown' if the protocol cannot be determined.

        Raises:
            KeywordException: If the StorageClass is not found.
        """
        sc_kw = KubectlGetStorageclassKeywords(self._ssh_connection, self._kubeconfig_path)
        sc_output = sc_kw.get_storageclasses()
        sc = sc_output.get_storageclass_by_name(storage_class_name)
        storage_type = sc.get_storage_type()

        if storage_type == _NETAPP_SAN_STORAGE_TYPE:
            storage_type = self._resolve_san_capability(sc)

        if storage_type == "unknown":
            get_logger().log_warning(f"StorageClass '{storage_class_name}' has unrecognized provisioner: " f"{sc.get_provisioner()}")
        else:
            get_logger().log_info(f"StorageClass '{storage_class_name}': capability={storage_type}")
        return storage_type

    def get_netapp_capabilities(self) -> List[str]:
        """List the NetApp capabilities the lab has a healthy backend for.

        Pairs every NetApp StorageClass on the cluster with the sanType of the
        healthy TridentBackendConfigs, so that a Fibre Channel lab reports
        'netapp-fc' and not the iSCSI capability its StorageClass also matches.

        Returns:
            List[str]: Sorted capabilities, e.g. ['netapp-fc', 'netapp-nfs'].
        """
        sc_kw = KubectlGetStorageclassKeywords(self._ssh_connection, self._kubeconfig_path)
        storage_types = set(sc_kw.get_storageclasses().get_available_storage_types())

        tbc_output = self._get_trident_backend_configs()

        capabilities = []
        for capability, (_, san_type) in _NETAPP_CAPABILITY_TO_BACKEND.items():
            expected_storage_type = _NETAPP_SAN_STORAGE_TYPE if san_type else capability
            if expected_storage_type not in storage_types:
                continue
            if self._get_healthy_netapp_backends(capability, tbc_output):
                capabilities.append(capability)

        return sorted(capabilities)

    def get_storage_class_name(self, capability: str) -> str:
        """Get the name of the StorageClass that serves a NetApp capability.

        StorageClass names come from the helm overrides of each lab, so they are
        read from the cluster instead of being hard-coded by the caller.

        Args:
            capability (str): One of 'netapp-nfs', 'netapp-iscsi', 'netapp-fc'.

        Returns:
            str: Name of the StorageClass serving the capability.

        Raises:
            KeywordException: If the capability is not a NetApp one, or if no
                StorageClass on the lab serves it.
        """
        self._validate_netapp_capability(capability)

        _, san_type = _NETAPP_CAPABILITY_TO_BACKEND[capability]
        expected_storage_type = _NETAPP_SAN_STORAGE_TYPE if san_type else capability

        sc_kw = KubectlGetStorageclassKeywords(self._ssh_connection, self._kubeconfig_path)
        storage_classes = sc_kw.get_storageclasses().get_storageclasses()
        candidates = [sc for sc in storage_classes if sc.get_storage_type() == expected_storage_type]

        if not candidates:
            raise KeywordException(f"No StorageClass serving the '{capability}' capability exists on this lab.")

        if san_type:
            candidates = self._select_san_storage_classes(candidates, capability)

        get_logger().log_info(f"StorageClass serving '{capability}': {candidates[0].get_name()}")
        return candidates[0].get_name()

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
        backend matching the capability has lastOperationStatus == Success. For
        the SAN capabilities the match is on both storageDriverName and sanType,
        because iSCSI and Fibre Channel share the ontap-san driver.

        Args:
            required_capability (str): One of 'netapp-nfs', 'netapp-iscsi', 'netapp-fc'.

        Raises:
            KeywordException: If no healthy backend is found for the capability.
        """
        self._validate_netapp_capability(required_capability)

        required_driver, required_san_type = _NETAPP_CAPABILITY_TO_BACKEND[required_capability]
        get_logger().log_info(f"Verifying NetApp backend for capability '{required_capability}' " f"(driver: {required_driver}, sanType: {required_san_type or 'n/a'})")

        healthy = self._get_healthy_netapp_backends(required_capability)
        if healthy:
            get_logger().log_info(f"Healthy NetApp backend found: {healthy[0].get_name()} " f"(driver={required_driver}, sanType={healthy[0].get_san_type() or 'n/a'}, status=Success)")
            return

        # Log every backend on the driver, whatever its protocol, so that a lab
        # configured for the wrong SAN protocol is obvious from the logs.
        tbc_output = self._get_trident_backend_configs()
        for tbc in tbc_output.get_configs_by_driver(required_driver):
            get_logger().log_info(f"  TBC '{tbc.get_name()}': driver={tbc.get_storage_driver_name()}, " f"sanType={tbc.get_san_type() or 'n/a'}, " f"status={tbc.get_last_operation_status()}, msg={tbc.get_message()}")

        raise KeywordException(f"No healthy NetApp backend for capability '{required_capability}'. " f"No TridentBackendConfig with driver '{required_driver}'" f"{f' and sanType {required_san_type}' if required_san_type else ''} " f"has lastOperationStatus=Success.")

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
            raise KeywordException(f"Cannot determine capability for StorageClass '{storage_class_name}'")

        if capability.startswith("netapp-"):
            self.assert_netapp_backend_available(capability)

        return capability

    def _validate_netapp_capability(self, capability: str) -> None:
        """Reject a capability that is not one of the NetApp ones.

        Args:
            capability (str): Capability to check.

        Raises:
            KeywordException: If the capability is not a NetApp capability.
        """
        if capability not in _NETAPP_CAPABILITY_TO_BACKEND:
            raise KeywordException(f"'{capability}' is not a NetApp capability. " f"Valid values: {list(_NETAPP_CAPABILITY_TO_BACKEND.keys())}")

    def _get_trident_backend_configs(self) -> KubectlGetTridentBackendConfigOutput:
        """Read the TridentBackendConfig resources from the cluster.

        Returns:
            KubectlGetTridentBackendConfigOutput: The parsed TBC resources.
        """
        tbc_kw = KubectlGetTridentBackendConfigKeywords(self._ssh_connection, self._kubeconfig_path)
        return tbc_kw.get_trident_backend_configs()

    def _get_healthy_netapp_backends(self, capability: str, tbc_output: KubectlGetTridentBackendConfigOutput = None) -> List[KubectlTridentBackendConfigObject]:
        """Get the healthy TridentBackendConfigs serving a NetApp capability.

        Args:
            capability (str): One of 'netapp-nfs', 'netapp-iscsi', 'netapp-fc'.
            tbc_output (KubectlGetTridentBackendConfigOutput, optional): Already
                retrieved TBC resources, to spare a second query when several
                capabilities are checked in a row. Read from the cluster if None.

        Returns:
            List[KubectlTridentBackendConfigObject]: Healthy backends for the capability.
        """
        driver, san_type = _NETAPP_CAPABILITY_TO_BACKEND[capability]
        tbc_output = tbc_output or self._get_trident_backend_configs()
        return tbc_output.get_healthy_configs_by_driver(driver, san_type)

    def _select_san_storage_classes(self, candidates: List[KubectlGetStorageclassObject], capability: str) -> List[KubectlGetStorageclassObject]:
        """Narrow SAN StorageClasses down to the ones serving a single SAN protocol.

        Every SAN StorageClass looks the same, so when a lab configures more than
        one SAN protocol they are told apart by the storagePools parameter, which
        pins a StorageClass to a named backend whose sanType is known.

        Args:
            candidates (List[KubectlGetStorageclassObject]): SAN StorageClasses found.
            capability (str): One of 'netapp-iscsi', 'netapp-fc'.

        Returns:
            List[KubectlGetStorageclassObject]: StorageClasses serving the capability.

        Raises:
            KeywordException: If several SAN StorageClasses exist and none of them
                is pinned to a backend of the requested protocol.
        """
        backend_names = {backend.get_backend_name() or backend.get_name() for backend in self._get_healthy_netapp_backends(capability)}
        pinned = [sc for sc in candidates if self._get_pinned_backend_names(sc) & backend_names]

        if pinned:
            return pinned

        if len(candidates) == 1:
            # A single SAN StorageClass serves whichever SAN backend exists, so
            # there is nothing to disambiguate.
            return candidates
        raise KeywordException(f"Cannot tell which StorageClass serves '{capability}': " f"{[sc.get_name() for sc in candidates]} all look like NetApp SAN and none is " f"pinned through storagePools to one of the {capability} backends {sorted(backend_names)}.")

    @staticmethod
    def _get_pinned_backend_names(storage_class: KubectlGetStorageclassObject) -> set:
        """Get the backend names a StorageClass is pinned to.

        Trident accepts 'storagePools' as 'backend1:pool1,pool2;backend2:.*', so
        the backend names are the part before each colon.

        Args:
            storage_class (KubectlGetStorageclassObject): StorageClass to inspect.

        Returns:
            set: Backend names, empty when the StorageClass pins none.
        """
        storage_pools = storage_class.get_parameters().get("storagePools", "")
        return {entry.split(":")[0].strip() for entry in storage_pools.split(";") if entry.strip()}

    def _resolve_san_capability(self, storage_class: KubectlGetStorageclassObject) -> str:
        """Resolve which SAN protocol a StorageClass serves, from its backend sanType.

        The StorageClass itself cannot say, so the answer comes from the backend it
        is pinned to through storagePools. An unpinned StorageClass serves whichever
        SAN backend exists, which only identifies a protocol when the lab serves one.

        Args:
            storage_class (KubectlGetStorageclassObject): The SAN StorageClass.

        Returns:
            str: 'netapp-iscsi' or 'netapp-fc', or 'unknown' when the StorageClass
                cannot be attributed to a single SAN protocol.
        """
        tbc_output = self._get_trident_backend_configs()
        pinned_backend_names = self._get_pinned_backend_names(storage_class)

        served_capabilities = []
        for capability, (_, san_type) in _NETAPP_CAPABILITY_TO_BACKEND.items():
            if not san_type:
                continue
            backends = self._get_healthy_netapp_backends(capability, tbc_output)
            if not backends:
                continue
            if pinned_backend_names & {backend.get_backend_name() or backend.get_name() for backend in backends}:
                return capability
            served_capabilities.append(capability)

        if pinned_backend_names or len(served_capabilities) != 1:
            return "unknown"
        return served_capabilities[0]
