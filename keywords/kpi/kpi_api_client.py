"""
KPI API Client — Orchestrates KPI data insertion into the database.

Provides easy-to-use functions for recording KPI measurements by
coordinating the underlying database operations.
"""

from typing import Any, Dict, Optional

from framework.database.operations.kpi_measure_operation import KpiMeasureOperation
from framework.database.operations.lab_runtime_config_operation import LabRuntimeConfigOperation
from framework.database.operations.run_operation import RunOperation
from framework.database.operations.standalone_session_operation import StandaloneSessionOperation
from framework.logging.automation_logger import get_logger


class KpiApiClient:
    """
    Client for inserting KPI data into the database.

    Orchestrates the operations needed to record KPI measurements.
    """

    def __init__(self):
        """
        Initialize the KPI API client.
        """
        self._lab_runtime_config_operation = LabRuntimeConfigOperation()
        self._run_operation = RunOperation()
        self._session_operation = StandaloneSessionOperation()
        self._measure_operation = KpiMeasureOperation()

    def create_lab_runtime_config(
        self,
        kernel_type: Optional[str] = None,
        cstate_setting: Optional[str] = None,
        pstate_setting: Optional[str] = None,
        per_core_config: Optional[bool] = None,
        hyperthreading_enabled: Optional[bool] = None,
        cpu_platform_cores: Optional[int] = None,
        cpu_application_cores: Optional[int] = None,
        cpu_application_isolated_cores: Optional[int] = None,
        hugepages_2m: Optional[int] = None,
        hugepages_1g: Optional[int] = None,
        network_latency_ms: Optional[float] = None,
        bandwidth_mbps: Optional[float] = None,
        host_labels: Optional[Dict[str, Any]] = None,
        installed_apps: Optional[Dict[str, Any]] = None,
        extra_config: Optional[Dict[str, Any]] = None,
        runtime_software_logs: Optional[str] = None,
    ) -> int:
        """
        Register a lab runtime configuration.

        Args:
            kernel_type: 'STD' or 'RT'.
            cstate_setting: e.g. 'Disabled', 'C1', 'C1E'.
            pstate_setting: e.g. 'P0', 'Enabled (P0)'.
            per_core_config: Per-core configuration active.
            hyperthreading_enabled: Hyperthreading state.
            cpu_platform_cores: Number of platform cores.
            cpu_application_cores: Number of application cores.
            cpu_application_isolated_cores: Number of isolated cores.
            hugepages_2m: 2MB hugepages count.
            hugepages_1g: 1GB hugepages count.
            network_latency_ms: Network latency in ms.
            bandwidth_mbps: Bandwidth in Mbps.
            host_labels: Per-host labels dict.
            installed_apps: Installed apps dict.
            extra_config: Additional configuration data.
            runtime_software_logs: Log collection setting.

        Returns:
            int: The lab_runtime_config_id.
        """
        get_logger().log_info("Creating lab_runtime_config")
        config_id = self._lab_runtime_config_operation.create_lab_runtime_config(
            kernel_type=kernel_type,
            cstate_setting=cstate_setting,
            pstate_setting=pstate_setting,
            per_core_config=per_core_config,
            hyperthreading_enabled=hyperthreading_enabled,
            cpu_platform_cores=cpu_platform_cores,
            cpu_application_cores=cpu_application_cores,
            cpu_application_isolated_cores=cpu_application_isolated_cores,
            hugepages_2m=hugepages_2m,
            hugepages_1g=hugepages_1g,
            network_latency_ms=network_latency_ms,
            bandwidth_mbps=bandwidth_mbps,
            host_labels=host_labels,
            installed_apps=installed_apps,
            extra_config=extra_config,
            runtime_software_logs=runtime_software_logs,
        )
        get_logger().log_info(f"Created lab_runtime_config_id: {config_id}")
        return config_id

    def create_standalone_run(
        self,
        run_name: str,
        product: str,
        run_type_id: int,
        build_info_id: int,
        platform_build_info_id: int,
    ) -> int:
        """
        Create a standalone run (without requiring a test plan).

        Args:
            run_name: Descriptive name for the run.
            product: Product name (e.g. 'WRCP').
            run_type_id: Run type ID.
            build_info_id: Build info ID for the software build.
            platform_build_info_id: Platform build info ID.

        Returns:
            int: The run_id.
        """
        get_logger().log_info(f"Creating standalone run '{run_name}'")
        run_id = self._run_operation.create_standalone_run(
            run_name, product, run_type_id, build_info_id, platform_build_info_id
        )
        get_logger().log_info(f"Created run_id: {run_id}")
        return run_id

    def create_standalone_session(
        self,
        run_id: int,
        lab_id: int,
        session_info_id: int,
        tag: str,
        sys_type: Optional[str] = None,
        kubernetes_version: Optional[str] = None,
        ceph_version: Optional[str] = None,
        lab_runtime_config_id: Optional[int] = None,
    ) -> str:
        """
        Create a standalone test session.

        Args:
            run_id: Run ID from create_standalone_run.
            lab_id: execution_target_id of the lab.
            session_info_id: Maps to a TestPlan's session_info_id.
            tag: Descriptive tag for the session.
            sys_type: System type (e.g. 'AIO-DX', 'Standard').
            kubernetes_version: K8s version.
            ceph_version: Ceph version.
            lab_runtime_config_id: ID from create_lab_runtime_config.

        Returns:
            str: The session_id (UUID string).
        """
        get_logger().log_info(f"Creating standalone session (tag='{tag}')")
        session_id = self._session_operation.create_standalone_session(
            run_id, lab_id, session_info_id, tag,
            sys_type=sys_type,
            kubernetes_version=kubernetes_version,
            ceph_version=ceph_version,
            lab_runtime_config_id=lab_runtime_config_id,
        )
        get_logger().log_info(f"Created session_id: {session_id}")
        return session_id

    def insert_kpi_measure(
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
        Insert a single KPI measurement.

        Args:
            kpi_id: KPI ID from the kpi catalog table.
            session_id: Session UUID from create_standalone_session.
            kpi_value: The measured value.
            test_case_result_id: Specific test execution UUID (for drill-down).
            kpi_baseline_id: Baseline to compare against.
            kpi_measure_details: Additional metadata dict.
            collected_at: ISO 8601 timestamp. Defaults to now.
            notes: Free-form notes.

        Returns:
            int: The kpi_measure_id.
        """
        get_logger().log_info(f"Inserting kpi_measure (kpi_id={kpi_id}, value={kpi_value})")
        measure_id = self._measure_operation.create_kpi_measure(
            kpi_id, session_id, kpi_value,
            test_case_result_id=test_case_result_id,
            kpi_baseline_id=kpi_baseline_id,
            kpi_measure_details=kpi_measure_details,
            collected_at=collected_at,
            notes=notes,
        )
        get_logger().log_info(f"Created kpi_measure_id: {measure_id}")
        return measure_id
