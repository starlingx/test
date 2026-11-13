"""Record Distributed Cloud phase-duration KPIs to the KPI datastore.

Maps a ``{phase: seconds}`` dict (from
:class:`DcManagerLogKpiKeywords.mine_phase_durations`) onto the DC KPI taxonomy
and delegates persistence to :class:`KpiRecorderKeywords`. Recording is
best-effort: when the run has no session or the database is disabled it is
skipped without failing the test.

Taxonomy:
    owner team = "Distributed Cloud"   (fixed)
    product    = "StarlingX"            (fixed)
    node role  = "subcloud"             (default; override per call)
    detail     = "duration"             (unit: seconds)
    category   = per scenario           (e.g. "Enrollment")
    group      = per scenario           (e.g. "dcmanager_enroll")
    kpi_name   = f"{name_prefix}-{phase}"

Variants (e.g. jcnr, release delta) are measurement tags passed via
``extra_details``, not new groups or categories. Lab, release and system type
come from the run's session.
"""

from typing import Any, Dict, Optional

from config.configuration_manager import ConfigurationManager
from framework.database.objects.kpi import Kpi
from framework.database.objects.kpi_measure import KpiMeasure
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.kpi.kpi_recorder_keywords import KpiRecorderKeywords

# Fixed across every DC KPI so they all group under one Owner team filter.
DC_KPI_OWNER_TEAM = "Distributed Cloud"
DC_KPI_PRODUCT = "StarlingX"
# Defaults for DC subcloud operations; override per call only if a scenario needs to.
DC_KPI_DEFAULT_NODE_ROLE = "subcloud"
DC_KPI_DEFAULT_DETAIL = "duration"
DC_KPI_DEFAULT_UNIT = "s"


class DcKpiRecorderKeywords(BaseKeyword):
    """Records DC phase-duration KPIs for any scenario to the KPI tables."""

    def record_phase_durations(
        self,
        durations: Dict[str, float],
        kpi_category: str,
        kpi_group: str,
        name_prefix: str,
        node_role: str = DC_KPI_DEFAULT_NODE_ROLE,
        subcloud_version: Optional[str] = None,
        system_controller_version: Optional[str] = None,
        extra_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a set of mined phase durations as KPI measurements.

        Builds one Kpi + KpiMeasure per phase and hands the batch to the
        framework recorder. Each KPI name is ``f"{name_prefix}-{phase}"`` so a
        scenario's phases sit together in the catalog.

        Two software versions can be captured and may differ (e.g. an N-1
        subcloud under an N system controller):
          - the subcloud's version -> the dedicated kpi_measure.kpi_subcloud_version
            column;
          - the system controller's version -> recorded as a
            "system_controller_version" measurement detail (no dedicated column).

        Args:
            durations (Dict[str, float]): phase name -> duration in seconds, as
                returned by DcManagerLogKpiKeywords.mine_phase_durations.
            kpi_category (str): KPI catalog category, e.g. "Enrollment" or
                "Backup_Restore".
            kpi_group (str): KPI catalog group, e.g. "dcmanager_enroll".
            name_prefix (str): KPI name prefix, e.g. "dcmanager-enroll".
            node_role (str): Node role for the KPIs. Defaults to "subcloud".
            subcloud_version (Optional[str]): The enrolled subcloud's software
                version. Stored in the kpi_subcloud_version column.
            system_controller_version (Optional[str]): The system controller's
                software version. Stored as a measurement detail tag.
            extra_details (Optional[Dict[str, Any]]): Variant/context tags merged
                into each measurement's details (e.g. {"jcnr": False}).
        """
        if not durations:
            get_logger().log_info("No phase durations to record")
            return

        lab_config = ConfigurationManager.get_lab_config()
        lab_name = lab_config.get_lab_name()
        lab_type = lab_config.get_lab_type()

        base_details: Dict[str, Any] = {"lab_name": lab_name, "lab_type": lab_type}
        if system_controller_version is not None:
            base_details["system_controller_version"] = system_controller_version
        if extra_details:
            base_details.update(extra_details)

        kpi_measures = []
        for phase_name, duration_seconds in durations.items():
            kpi = Kpi(
                product=DC_KPI_PRODUCT,
                kpi_category=kpi_category,
                kpi_name=f"{name_prefix}-{phase_name}",
                kpi_node_role=node_role,
                kpi_detail=DC_KPI_DEFAULT_DETAIL,
                kpi_group=kpi_group,
                kpi_unit=DC_KPI_DEFAULT_UNIT,
                kpi_owner_team=DC_KPI_OWNER_TEAM,
                kpi_description=f"{name_prefix} {phase_name} phase duration",
            )
            kpi_measures.append(
                KpiMeasure(
                    kpi=kpi,
                    kpi_value=duration_seconds,
                    kpi_measure_details=dict(base_details, phase=phase_name),
                    kpi_subcloud_version=subcloud_version,
                    notes=f"{name_prefix}-{phase_name} on {lab_name}",
                )
            )

        get_logger().log_info(f"Recording {len(kpi_measures)} DC KPI measurements (category={kpi_category}, group={kpi_group}, sc_version={system_controller_version}, subcloud_version={subcloud_version})")
        KpiRecorderKeywords().record_kpi_measures(kpi_measures)

    def record_wall_clock_duration(
        self,
        duration_seconds: float,
        kpi_category: str,
        kpi_group: str,
        name_prefix: str,
        phase: str = "total",
        node_role: str = DC_KPI_DEFAULT_NODE_ROLE,
        subcloud_version: Optional[str] = None,
        system_controller_version: Optional[str] = None,
        extra_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a single wall-clock duration as one KPI measurement.

        For operations whose duration is measured by the test's own clock rather
        than mined from platform log markers (e.g. a subcloud backup). It delegates
        to record_phase_durations so the taxonomy, tags and persistence are
        identical to the mined KPIs; the only difference is that the single
        ``{phase: duration}`` entry comes from the wall clock.

        Args:
            duration_seconds (float): Measured duration in seconds.
            kpi_category (str): KPI catalog category, e.g. "Backup_Restore".
            kpi_group (str): KPI catalog group, e.g. "dcmanager_central_backup".
            name_prefix (str): KPI name prefix, e.g. "dcmanager-central-backup".
            phase (str): Phase name for the single measurement. Defaults to "total".
            node_role (str): Node role for the KPI. Defaults to "subcloud".
            subcloud_version (Optional[str]): The subcloud's software version.
            system_controller_version (Optional[str]): The system controller's version.
            extra_details (Optional[Dict[str, Any]]): Variant/context tags.
        """
        self.record_phase_durations(
            {phase: float(duration_seconds)},
            kpi_category=kpi_category,
            kpi_group=kpi_group,
            name_prefix=name_prefix,
            node_role=node_role,
            subcloud_version=subcloud_version,
            system_controller_version=system_controller_version,
            extra_details=extra_details,
        )
