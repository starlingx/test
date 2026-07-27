from framework.logging.automation_logger import get_logger


class CpuUsageKpiHelperObject:
    """Records cyclictest CPU usage KPIs via the ACE logger."""

    # KPI name templates: (kernel, c_state_label, p_state_label) -> prefix
    _PREFIX_MAP = {
        ("rt", "c0", "p1"): "CPU_USAGE_RT_C0P1",
        ("rt", "c1", "p1"): "CPU_USAGE_RT_C1P1",
        ("rt", "c1", "p0"): "CPU_USAGE_RT_C1P0",
        ("rt", "c0", "p0"): "CPU_USAGE_RT_C0P0",
        ("std", "c0", "p1"): "CPU_USAGE_STD_C0P1",
        ("std", "c1", "p1"): "CPU_USAGE_STD_C1P1",
        ("std", "c1", "p0"): "CPU_USAGE_STD_C1P0",
        ("std", "c0", "p0"): "CPU_USAGE_STD_C0P0",
    }

    def __init__(self, cpu_states: dict, kernel_mode: str):
        """Initialize the KPI helper with CPU state and kernel mode.

        Args:
            cpu_states (dict): e.g. {"c_state": "Enable", "p_state": "Disable"}
            kernel_mode (str): "rt" or "std"
        """
        c = "c1" if cpu_states.get("c_state") == "Enable" else "c0"
        p = "p1" if cpu_states.get("p_state") == "Enable" else "p0"
        self._prefix = self._PREFIX_MAP.get(
            (kernel_mode, c, p),
            f"CPU_USAGE_{kernel_mode.upper()}_{c.upper()}{p.upper()}",
        )

    def set_kpi(self, kpi_values: dict) -> None:
        """Log CPU usage KPI values via the ACE logger.

        Args:
            kpi_values (dict): e.g. {"iso_avg": 12.3, "iso_median": 11.0, "iso_deviation": 0.5}
        """
        for key, value in kpi_values.items():
            kpi_name = f"{self._prefix}_{key.upper()}"
            get_logger().log_info(f"{kpi_name}: {value}")
