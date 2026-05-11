"""Output parser for kubectl get tridentbackendconfig -o json."""

import json
from typing import List

from framework.exceptions.keyword_exception import KeywordException
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
            tbc_obj.set_backend_name(spec.get("backendName", ""))
            tbc_obj.set_last_operation_status(status.get("lastOperationStatus", ""))
            tbc_obj.set_message(status.get("message", ""))

            self._configs.append(tbc_obj)

    def get_trident_backend_configs(self) -> List[KubectlTridentBackendConfigObject]:
        """Get all parsed TridentBackendConfig objects.

        Returns:
            List[KubectlTridentBackendConfigObject]: List of TBC objects.
        """
        return self._configs

    def get_configs_by_driver(self, driver_name: str) -> List[KubectlTridentBackendConfigObject]:
        """Get TBCs filtered by storage driver name.

        Args:
            driver_name (str): Driver name (e.g. 'ontap-nas', 'ontap-san').

        Returns:
            List[KubectlTridentBackendConfigObject]: Matching TBCs.
        """
        return [c for c in self._configs if c.get_storage_driver_name() == driver_name]

    def get_healthy_configs_by_driver(self, driver_name: str) -> List[KubectlTridentBackendConfigObject]:
        """Get healthy TBCs filtered by storage driver name.

        Args:
            driver_name (str): Driver name.

        Returns:
            List[KubectlTridentBackendConfigObject]: Healthy TBCs matching the driver.
        """
        return [c for c in self._configs if c.get_storage_driver_name() == driver_name and c.is_healthy()]

    def has_healthy_backend_for_driver(self, driver_name: str) -> bool:
        """Check if at least one healthy backend exists for the given driver.

        Args:
            driver_name (str): Driver name.

        Returns:
            bool: True if a healthy backend exists.
        """
        return len(self.get_healthy_configs_by_driver(driver_name)) > 0
