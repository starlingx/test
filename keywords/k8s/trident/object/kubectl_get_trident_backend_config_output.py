"""Output parser for kubectl get tridentbackendconfig -o json."""

import json
from typing import List, Optional

from framework.logging.automation_logger import get_logger
from keywords.k8s.trident.object.kubectl_trident_backend_config_object import KubectlTridentBackendConfigObject


class KubectlGetTridentBackendConfigOutput:
    """Parses kubectl get tridentbackendconfig -o json output."""

    def __init__(self, output: str) -> None:
        """Initialize and parse the kubectl output.

        Args:
            output (str): Raw JSON output from kubectl get tbc -o json.
        """
        self._configs: List[KubectlTridentBackendConfigObject] = []
        self._parse(output)

    def _parse(self, output: str) -> None:
        """Parse JSON output into TridentBackendConfig objects.

        Args:
            output (str): Raw JSON string.
        """
        raw = output if isinstance(output, str) else "\n".join(output)

        json_start = raw.find("{")
        if json_start == -1:
            get_logger().log_warning("No JSON found in tridentbackendconfig output")
            return

        json_str = raw[json_start:]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            get_logger().log_warning(f"Failed to parse tridentbackendconfig JSON: {e}")
            return

        items = data.get("items", []) if "items" in data else [data]

        for item in items:
            tbc_obj = KubectlTridentBackendConfigObject()
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})

            tbc_obj.set_name(metadata.get("name", ""))
            tbc_obj.set_namespace(metadata.get("namespace", ""))
            tbc_obj.set_storage_driver_name(spec.get("storageDriverName", ""))
            # The chart does not render spec.backendName, so fall back to the name
            # Trident reports once the backend is bound.
            backend_name = spec.get("backendName", "") or status.get("backendInfo", {}).get("backendName", "")
            tbc_obj.set_backend_name(backend_name)
            tbc_obj.set_management_lif(spec.get("managementLIF", ""))
            tbc_obj.set_data_lif(spec.get("dataLIF", ""))
            tbc_obj.set_svm(spec.get("svm", ""))
            tbc_obj.set_nfs_mount_options(spec.get("nfsMountOptions", ""))
            tbc_obj.set_credentials_secret_name(spec.get("credentials", {}).get("name", ""))
            tbc_obj.set_last_operation_status(status.get("lastOperationStatus", ""))
            tbc_obj.set_message(status.get("message", ""))
            tbc_obj.set_phase(status.get("phase", ""))
            tbc_obj.set_san_type(spec.get("sanType", ""))

            self._configs.append(tbc_obj)

    def get_trident_backend_configs(self) -> List[KubectlTridentBackendConfigObject]:
        """Get all parsed TridentBackendConfig objects.

        Returns:
            List[KubectlTridentBackendConfigObject]: List of TBC objects.
        """
        return self._configs

    def get_configs_by_driver(self, driver_name: str, san_type: str = None) -> List[KubectlTridentBackendConfigObject]:
        """Get TBCs filtered by storage driver name, and optionally by SAN type.

        The three SAN protocols all use the 'ontap-san' driver, so the driver
        alone does not identify a protocol; pass san_type to select one of them.

        Args:
            driver_name (str): Driver name, either 'ontap-nas' or 'ontap-san'.
            san_type (str, optional): SAN type to match ('fcp', 'iscsi', 'nvme').
                If None, backends are matched on the driver name alone.

        Returns:
            List[KubectlTridentBackendConfigObject]: Matching TBCs.
        """
        matching = [c for c in self._configs if c.get_storage_driver_name() == driver_name]
        if san_type is None:
            return matching
        return [c for c in matching if self._normalize_san_type(c.get_san_type()) == san_type]

    def get_healthy_configs_by_driver(self, driver_name: str, san_type: str = None) -> List[KubectlTridentBackendConfigObject]:
        """Get healthy TBCs filtered by storage driver name, and optionally by SAN type.

        Args:
            driver_name (str): Driver name, either 'ontap-nas' or 'ontap-san'.
            san_type (str, optional): SAN type to match ('fcp', 'iscsi', 'nvme').
                If None, backends are matched on the driver name alone.

        Returns:
            List[KubectlTridentBackendConfigObject]: Healthy TBCs matching the filters.
        """
        return [c for c in self.get_configs_by_driver(driver_name, san_type) if c.is_healthy()]

    def has_healthy_backend_for_driver(self, driver_name: str, san_type: str = None) -> bool:
        """Check if at least one healthy backend exists for the given driver and SAN type.

        Args:
            driver_name (str): Driver name, either 'ontap-nas' or 'ontap-san'.
            san_type (str, optional): SAN type to match ('fcp', 'iscsi', 'nvme').
                If None, backends are matched on the driver name alone.

        Returns:
            bool: True if a healthy backend exists.
        """
        return len(self.get_healthy_configs_by_driver(driver_name, san_type)) > 0

    @staticmethod
    def _normalize_san_type(san_type: str) -> str:
        """Resolve an unset sanType to the Trident default.

        Trident treats a SAN backend with no sanType as iSCSI, so an empty value
        has to compare equal to 'iscsi' rather than to nothing.

        Args:
            san_type (str): SAN type as read from spec.sanType.

        Returns:
            str: The sanType, or 'iscsi' when it is unset.
        """
        return san_type or "iscsi"

    def get_bound_nas_backend(self) -> Optional[KubectlTridentBackendConfigObject]:
        """Get the first bound ontap-nas backend.

        Returns:
            Optional[KubectlTridentBackendConfigObject]: The bound NAS backend,
                or None if no bound ontap-nas backend exists.
        """
        for config in self._configs:
            if config.get_storage_driver_name() == "ontap-nas" and config.is_bound():
                return config
        return None

    def get_bound_san_backends(self) -> List[KubectlTridentBackendConfigObject]:
        """Get all bound ontap-san backends (iSCSI and FC).

        Returns:
            List[KubectlTridentBackendConfigObject]: List of bound SAN backends.
        """
        return [c for c in self._configs if c.get_storage_driver_name() == "ontap-san" and c.is_bound()]
