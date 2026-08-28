from typing import Any, Dict, Optional

from framework.database.objects.kpi import Kpi


class KpiMeasure:
    """
    Class for a single KPI measurement.

    Holds the measured value for a KPI along with optional metadata. The
    associated Kpi object describes what is being measured.
    """

    def __init__(
        self,
        kpi: Kpi,
        kpi_value: float,
        kpi_measure_details: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
        collected_at: Optional[str] = None,
    ):
        """
        Constructor for KpiMeasure.

        Args:
            kpi (Kpi): The KPI this measurement belongs to.
            kpi_value (float): The measured value.
            kpi_measure_details (Optional[Dict[str, Any]]): Additional metadata.
            notes (Optional[str]): Free-form notes.
            collected_at (Optional[str]): ISO 8601 timestamp. Defaults to now.
        """
        self.kpi = kpi
        self.kpi_value = kpi_value
        self.kpi_measure_details = kpi_measure_details
        self.notes = notes
        self.collected_at = collected_at

    def get_kpi(self) -> Kpi:
        """Getter for the associated KPI.

        Returns:
            Kpi: The KPI this measurement belongs to.
        """
        return self.kpi

    def get_kpi_value(self) -> float:
        """Getter for the measured value.

        Returns:
            float: The measured value.
        """
        return self.kpi_value

    def get_kpi_measure_details(self) -> Optional[Dict[str, Any]]:
        """Getter for the measurement details.

        Returns:
            Optional[Dict[str, Any]]: Additional metadata.
        """
        return self.kpi_measure_details

    def get_notes(self) -> Optional[str]:
        """Getter for notes.

        Returns:
            Optional[str]: Free-form notes.
        """
        return self.notes

    def get_collected_at(self) -> Optional[str]:
        """Getter for the collection timestamp.

        Returns:
            Optional[str]: ISO 8601 timestamp.
        """
        return self.collected_at
