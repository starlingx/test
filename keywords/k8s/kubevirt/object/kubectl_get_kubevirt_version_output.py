"""Output parser for kubectl get kubevirt -A -o json."""

import json

from framework.logging.automation_logger import get_logger
from keywords.k8s.kubevirt.object.kubevirt_version_object import (
    KubeVirtVersionObject,
)


class KubectlGetKubevirtVersionOutput:
    """Parses JSON output from kubectl get kubevirt -A -o json.

    If the KubeVirt CR is absent (empty items list), the version
    object remains in the default not-installed state.
    """

    def __init__(self, kubectl_output: str) -> None:
        """Parse kubectl JSON output into a KubeVirtVersionObject.

        Args:
            kubectl_output (str): Raw JSON string from kubectl.
        """
        self._kubevirt_version = KubeVirtVersionObject()
        self._parse(kubectl_output)

    def _parse(self, kubectl_output: str) -> None:
        """Parse the JSON and populate the version object.

        Args:
            kubectl_output (str): Raw JSON string from kubectl.
        """
        if not kubectl_output or not kubectl_output.strip():
            get_logger().log_info(
                "KubeVirt kubectl output is empty — not installed"
            )
            return

        try:
            parsed = json.loads(kubectl_output)
        except json.JSONDecodeError as e:
            get_logger().log_info(
                f"KubeVirt output is not valid JSON ({e}) "
                "— not installed"
            )
            return

        items = parsed.get("items", [])
        if not items:
            get_logger().log_info(
                "KubeVirt CR items list is empty — not installed"
            )
            return

        status = items[0].get("status", {})
        self._kubevirt_version.set_installed(True)
        self._kubevirt_version.set_observed_version(
            status.get("observedKubeVirtVersion")
        )
        self._kubevirt_version.set_target_version(
            status.get("targetKubeVirtVersion")
        )
        self._kubevirt_version.set_operator_version(
            status.get("operatorVersion")
        )

    def get_kubevirt_version(self) -> KubeVirtVersionObject:
        """Return the parsed KubeVirt version object.

        Returns:
            KubeVirtVersionObject: The version data.
        """
        return self._kubevirt_version
