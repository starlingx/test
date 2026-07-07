"""Output parser for kubectl get configmap JSON response."""

import json
from typing import Union

from keywords.k8s.configmap.object.kubectl_configmap_object import KubectlConfigmapObject


class KubectlGetConfigmapOutput:
    """Parses kubectl get configmap JSON output into a ConfigMap object."""

    def __init__(self, raw_output: Union[str, list]) -> None:
        """Initialize and parse the raw kubectl output.

        Args:
            raw_output (Union[str, list]): Raw JSON output from kubectl get configmap -o json.
        """
        if isinstance(raw_output, list):
            raw_output = "\n".join(raw_output)
        self.configmap = self._build_configmap_object(raw_output)

    def _build_configmap_object(self, raw_json: str) -> KubectlConfigmapObject:
        """Build a ConfigMap object from raw JSON string.

        Args:
            raw_json (str): JSON string from kubectl output.

        Returns:
            KubectlConfigmapObject: Parsed ConfigMap object.

        Raises:
            ValueError: If JSON parsing fails.
        """
        parsed = json.loads(raw_json)
        configmap = KubectlConfigmapObject()
        configmap.set_name(parsed.get("metadata", {}).get("name", ""))
        configmap.set_namespace(parsed.get("metadata", {}).get("namespace", ""))
        configmap.set_data(parsed.get("data", {}))
        return configmap

    def get_configmap(self) -> KubectlConfigmapObject:
        """Get the parsed ConfigMap object.

        Returns:
            KubectlConfigmapObject: The parsed ConfigMap.
        """
        return self.configmap
