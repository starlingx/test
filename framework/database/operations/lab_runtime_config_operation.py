import json
from typing import Any, Dict, Optional

from framework.database.connection.database_operation_manager import DatabaseOperationManager


class LabRuntimeConfigOperation:
    """
    Database operations for the lab_runtime_config table.
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

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
        Creates a lab_runtime_config record in the database.

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

        Raises:
            ValueError: If unable to insert the record.
        """
        host_labels_json = json.dumps(host_labels) if host_labels else '{}'
        installed_apps_json = json.dumps(installed_apps) if installed_apps else '{}'
        extra_config_json = json.dumps(extra_config) if extra_config else '{}'

        insert_query = (
            "INSERT INTO lab_runtime_config ("
            "kernel_type, cstate_setting, pstate_setting, "
            "per_core_config, hyperthreading_enabled, "
            "cpu_platform_cores, cpu_application_cores, cpu_application_isolated_cores, "
            "hugepages_2m, hugepages_1g, "
            "network_latency_ms, bandwidth_mbps, "
            "host_labels, installed_apps, extra_config, "
            "runtime_software_logs"
            ") VALUES ("
            f"'{kernel_type}', '{cstate_setting}', '{pstate_setting}', "
            f"{per_core_config}, {hyperthreading_enabled}, "
            f"{cpu_platform_cores}, {cpu_application_cores}, {cpu_application_isolated_cores}, "
            f"{hugepages_2m}, {hugepages_1g}, "
            f"{network_latency_ms}, {bandwidth_mbps}, "
            f"'{host_labels_json}', '{installed_apps_json}', '{extra_config_json}', "
            f"'{runtime_software_logs}'"
            ") RETURNING lab_runtime_config_id"
        )

        results = self.database_operation_manager.execute_query(insert_query)

        if results:
            return results[0][0]

        raise ValueError("Unable to insert lab_runtime_config.")
