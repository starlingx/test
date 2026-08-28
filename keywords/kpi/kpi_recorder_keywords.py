"""
KPI Recorder Keywords — Framework-level recording of KPI measurements.

Accepts KpiMeasure objects and persists them to the kpi and kpi_measure
tables, handling session resolution and the underlying KPI catalog and
measurement inserts. Tests build KpiMeasure objects and delegate all
persistence concerns to this class.
"""

from typing import List

from config.configuration_manager import ConfigurationManager
from framework.database.objects.kpi_measure import KpiMeasure
from framework.logging.automation_logger import get_logger
from framework.runner.objects.run_context_manager import RunContextManager
from keywords.base_keyword import BaseKeyword
from keywords.kpi.kpi_api_client import KpiApiClient


class KpiRecorderKeywords(BaseKeyword):
    """
    Keywords for recording KPI measurements into the new KPI tables.
    """

    def __init__(self):
        """
        Initialize the KPI recorder.
        """
        self._kpi_client = KpiApiClient()

    def record_kpi_measures(self, kpi_measures: List[KpiMeasure]) -> None:
        """
        Record a list of KPI measurements to the kpi and kpi_measure tables.

        Measurements are anchored to the session supplied by the run context.
        A run that was not given a session has nothing to attach the KPIs to,
        so the upload is skipped rather than creating a run mid-test-execution.

        Args:
            kpi_measures (List[KpiMeasure]): The measurements to record.
        """
        if not kpi_measures:
            get_logger().log_info("No KPI measures to record")
            return

        if not ConfigurationManager.get_database_config().use_database():
            get_logger().log_info("Database is disabled, skipping KPI recording")
            return

        session_id = RunContextManager.get_session_id()
        if not session_id:
            get_logger().log_info("This run has no session id, so the KPI measures were not recorded.")
            return

        try:
            for measure in kpi_measures:
                kpi = measure.get_kpi()
                kpi_id = self._kpi_client.get_or_create_kpi(
                    product=kpi.get_product(),
                    kpi_category=kpi.get_kpi_category(),
                    kpi_name=kpi.get_kpi_name(),
                    kpi_node_role=kpi.get_kpi_node_role(),
                    kpi_detail=kpi.get_kpi_detail(),
                    kpi_group=kpi.get_kpi_group(),
                    kpi_unit=kpi.get_kpi_unit(),
                    kpi_owner_team=kpi.get_kpi_owner_team(),
                    kpi_description=kpi.get_kpi_description(),
                )

                self._kpi_client.insert_kpi_measure(
                    kpi_id=kpi_id,
                    session_id=session_id,
                    kpi_value=measure.get_kpi_value(),
                    kpi_measure_details=measure.get_kpi_measure_details(),
                    collected_at=measure.get_collected_at(),
                    notes=measure.get_notes(),
                )

            get_logger().log_info(f"=== Recorded {len(kpi_measures)} KPI measurements ===")

        except Exception as e:
            get_logger().log_error(f"Failed to record KPI measures: {e}")
            get_logger().log_info("Continuing execution despite KPI recording failure")
