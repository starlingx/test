"""Keywords for generating Platform CPU load as a host process to raise the 100.101 alarm.

The alarm is accounted against Platform cores only, which the static CPU
manager excludes from the Kubernetes cpuset on worker/AIO hosts, so a pod
cannot be pinned to them. The load is therefore run as a host process via
``systemd-run`` transient services (one per core), which run outside the
quota-limited ``utils.slice`` that SSH sessions land in; a plain backgrounded
command there is throttled and never saturates the cores. Each service is
pinned with ``AllowedCPUs`` and capped with ``CPUQuota`` (see
:data:`DEFAULT_CPU_LOAD_PERCENT`).

Detection uses :func:`PlatformCpuStressKeywords.wait_for_cpu_alarm` rather than
``AlarmListKeywords`` because ``fm alarm-list`` runs slowly on the saturated
Platform cores and needs the extended :data:`ALARM_QUERY_COMMAND_TIMEOUT`,
which the shared wait helpers do not expose.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_output import AlarmListOutput

CPU_ALARM_ID = "100.101"

# Prefix/glob for the transient systemd service units (one per stressed core).
UNIT_PREFIX = "platform-cpu-stress"

# Dedicated slice so the services run outside utils.slice's CPU cap.
STRESS_SLICE = "platform-cpu-stress.slice"

# Must exceed the 95% alarm threshold; 97% trips it reliably while leaving
# headroom so the platform's own FM CLI/API stay responsive.
DEFAULT_CPU_LOAD_PERCENT = 97

# Extended timeout for 'fm alarm-list': the FM CLI runs on the saturated
# cores and exceeds the framework default (60s).
ALARM_QUERY_COMMAND_TIMEOUT = 180


class PlatformCpuStressKeywords(BaseKeyword):
    """Keywords to generate and release Platform CPU load on a host."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize PlatformCpuStressKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host whose
                Platform cores are to be stressed. This must be a connection to
                the host itself (e.g. the active controller), because the load
                runs as a host process pinned to Platform cores.
        """
        self.ssh_connection = ssh_connection

    def start_platform_cpu_stress(self, platform_cores: list[int], cpu_load_percent: int = DEFAULT_CPU_LOAD_PERCENT) -> None:
        """Start one transient systemd service per Platform core, each pinned and load-capped.

        Each service runs via ``systemd-run`` (outside ``utils.slice``), confined
        to one core with ``AllowedCPUs`` and capped at ``cpu_load_percent`` via
        ``CPUQuota``.

        Args:
            platform_cores (list[int]): Logical core IDs to load (one service each).
            cpu_load_percent (int): Target load per core (1-100). Defaults to
                :data:`DEFAULT_CPU_LOAD_PERCENT`; must exceed the 95% threshold.

        Raises:
            ValueError: If ``platform_cores`` is empty or ``cpu_load_percent``
                is outside 1-100.
        """
        if not platform_cores:
            raise ValueError("No Platform cores supplied; cannot generate Platform CPU load.")
        if not 1 <= cpu_load_percent <= 100:
            raise ValueError(f"cpu_load_percent must be in 1-100, got {cpu_load_percent}")

        get_logger().log_info(f"Starting Platform CPU stress on cores {platform_cores} at {cpu_load_percent}% per core (one systemd service per core)")
        for core in platform_cores:
            unit = f"{UNIT_PREFIX}-{core}"
            # Transient service outside utils.slice; CPUQuota caps it to <pct>%
            # of the single core it is pinned to via AllowedCPUs.
            cmd = f'systemd-run --unit={unit} --slice={STRESS_SLICE} --collect --property=CPUQuota={cpu_load_percent}% --property=AllowedCPUs={core} sh -c "while :; do :; done"'
            self.ssh_connection.send_as_sudo_non_interactive(cmd)
        get_logger().log_info(f"Started {len(platform_cores)} Platform CPU stress services")

    def stop_platform_cpu_stress(self) -> None:
        """Stop all Platform CPU stress services started by this keyword.

        Stops every transient unit matching :data:`UNIT_PREFIX` via
        ``systemctl stop`` (which kills the whole service cgroup). Best-effort
        and idempotent: safe to call even if no services are running.
        """
        get_logger().log_info("Stopping Platform CPU stress services")
        # Stop every transient unit and its cgroup; 'true' keeps exit code 0 if none exist.
        cmd = f"systemctl stop '{UNIT_PREFIX}-*.service' 2>/dev/null; true"
        self.ssh_connection.send_as_sudo_non_interactive(cmd)

    def _is_cpu_alarm_present(self, hostname: str) -> bool:
        """Query 'fm alarm-list' (with extended timeout) and report 100.101 presence for a host.

        Uses :data:`ALARM_QUERY_COMMAND_TIMEOUT` since the FM CLI runs slowly on
        the saturated Platform cores.

        Args:
            hostname (str): Host whose alarm to look for (``host=<hostname>``).

        Returns:
            bool: True if alarm 100.101 is present for ``hostname``.
        """
        output = self.ssh_connection.send(source_openrc("fm alarm-list --nowrap"), command_timeout=ALARM_QUERY_COMMAND_TIMEOUT)
        for alarm in AlarmListOutput(output).get_alarms():
            if alarm.get_alarm_id() == CPU_ALARM_ID and f"host={hostname}" in (alarm.get_entity_id() or ""):
                return True
        return False

    def wait_for_cpu_alarm(self, hostname: str, present: bool, timeout: int = 600, check_interval: int = 15) -> None:
        """Poll until the Platform CPU alarm (100.101) reaches the desired presence state.

        Uses :func:`_is_cpu_alarm_present` (extended per-command timeout) rather
        than ``AlarmListKeywords``, whose wait helpers use the default timeout.

        Args:
            hostname (str): Host whose alarm to track (``host=<hostname>``).
            present (bool): True to wait for the alarm to appear, False to clear.
            timeout (int): Overall wait budget in seconds. Defaults to 600.
            check_interval (int): Seconds between polls. Defaults to 15.

        Raises:
            TimeoutError: If the alarm does not reach the desired state in time.
        """
        state = "appear" if present else "clear"
        validate_equals_with_retry(
            lambda: self._is_cpu_alarm_present(hostname),
            present,
            f"Platform CPU alarm {CPU_ALARM_ID} to {state} on {hostname}",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )
