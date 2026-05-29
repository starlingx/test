"""Trident backend output parser."""

from typing import List

from framework.logging.automation_logger import get_logger
from keywords.k8s.trident.object.trident_backend_object import TridentBackendObject


class TridentBackendOutput:
    """Parses kubectl get tridentbackends JSON output into objects.

    Accepts raw output from kubectl get tridentbackends -n trident
    with jsonpath formatting and produces TridentBackendObject instances.

    Sample raw output parsed by this class::

        [fdff:12:34:567::3] stx_021_sc1_svm0
        [fdff:11:23:456::3] stx_dc_021_sc3_svm0

    Each line contains a space-separated dataLIF and SVM name pair
    extracted via jsonpath: '{range .items[*]}{.config.dataLIF} {.config.svm}{"\\n"}{end}'
    """

    def __init__(self, raw_output: str) -> None:
        """Initialize and parse the raw kubectl output.

        Args:
            raw_output (str): Raw output from kubectl jsonpath query.
                Expected format: lines of 'dataLIF svm' pairs.
        """
        self._backends: List[TridentBackendObject] = []
        self._parse(raw_output)

    def _parse(self, raw_output: str) -> None:
        """Parse raw output into TridentBackendObject instances.

        Args:
            raw_output (str): Raw kubectl output with dataLIF/SVM pairs.
        """
        lines = raw_output if isinstance(raw_output, list) else str(raw_output).strip().splitlines()

        for line in lines:
            parts = line.strip().strip("'").split()
            if len(parts) >= 2:
                data_lif = parts[0]
                svm = parts[1]
                if data_lif and svm:
                    backend = TridentBackendObject()
                    backend.set_data_lif(data_lif)
                    backend.set_svm(svm)
                    self._backends.append(backend)

    def get_backends(self) -> List[TridentBackendObject]:
        """Get all parsed trident backends.

        Returns:
            List[TridentBackendObject]: List of backend objects.
        """
        return self._backends

    def get_first_backend(self) -> TridentBackendObject:
        """Get the first trident backend.

        Returns:
            TridentBackendObject: First backend object.

        Raises:
            IndexError: If no backends were found.
        """
        if not self._backends:
            raise IndexError("No trident backends found")
        return self._backends[0]

    def has_backends(self) -> bool:
        """Check if any backends were found.

        Returns:
            bool: True if at least one backend exists.
        """
        return len(self._backends) > 0

    def get_data_lif(self) -> str:
        """Get the dataLIF address from the first trident backend.

        Convenience method for callers that only need the dataLIF.

        Returns:
            str: DataLIF address or empty string if not found.
        """
        if not self._backends:
            get_logger().log_warning("No trident backends found")
            return ""
        return self._backends[0].get_data_lif()
