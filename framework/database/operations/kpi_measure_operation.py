import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from framework.database.connection.database_operation_manager import DatabaseOperationManager


class KpiMeasureOperation:
    """
    Database operations for the kpi_measure table.
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def create_kpi_measure(
        self,
        kpi_id: int,
        session_id: str,
        kpi_value: float,
        test_case_result_id: Optional[str] = None,
        kpi_baseline_id: Optional[int] = None,
        kpi_measure_details: Optional[Dict[str, Any]] = None,
        collected_at: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """
        Inserts a KPI measurement into the database.

        Args:
            kpi_id: KPI ID from the kpi catalog table.
            session_id: Session UUID.
            kpi_value: The measured value.
            test_case_result_id: Specific test execution UUID (for drill-down).
            kpi_baseline_id: Baseline to compare against.
            kpi_measure_details: Additional metadata dict.
            collected_at: ISO 8601 timestamp. Defaults to now.
            notes: Free-form notes.

        Returns:
            int: The kpi_measure_id.

        Raises:
            ValueError: If unable to insert the measurement.
        """
        if collected_at is None:
            collected_at = datetime.now(timezone.utc).isoformat()

        details_json = json.dumps(kpi_measure_details) if kpi_measure_details else '{}'
        test_case_result_id = f"'{test_case_result_id}'" if test_case_result_id is not None else "NULL"
        baseline_val = f"{kpi_baseline_id}" if kpi_baseline_id is not None else "NULL"
        notes_val = f"'{notes}'" if notes is not None else "NULL"

        insert_query = (
            "INSERT INTO kpi_measure ("
            "kpi_id, session_id, test_case_result_id, "
            "kpi_value, kpi_measure_details, "
            "kpi_baseline_id, collected_at, is_displayed, notes"
            ") VALUES ("
            f"{kpi_id}, '{session_id}', {test_case_result_id}, "
            f"{kpi_value}, '{details_json}', "
            f"{baseline_val}, '{collected_at}', true, {notes_val}"
            ") RETURNING kpi_measure_id"
        )

        results = self.database_operation_manager.execute_query(insert_query)

        if results:
            return results[0][0]

        raise ValueError("Unable to insert kpi_measure.")
