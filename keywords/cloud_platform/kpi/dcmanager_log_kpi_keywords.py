"""Mine DC operation phase durations from the system controller logs.

Each phase is bounded by a start and stop marker that the platform already
writes; a phase duration is the difference between those two log timestamps
(platform-truth, not the test's wall clock). The caller snapshots the log size
before the operation and passes it as ``since_line`` so only the lines appended
by this run are mined. Logs are root-only, so reads use sudo.

The dcmanager and state logs are registered by default; other logs can be added
per instance (constructor ``extra_logs`` or ``register_log``) so the same miner
serves other operations whose markers live in different logs. Timestamps are
expected in the platform form ``YYYY-MM-DD HH:MM:SS`` (UTC).
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.kpi.kpi_log_phase import KpiLogPhase

# System controller log paths (root-only).
DCMANAGER_LOG = "/var/log/dcmanager/dcmanager.log"
STATE_LOG = "/var/log/dcmanager/state.log"

# Default logical log name -> absolute path, matching the phase "log" token.
# Extend per instance via the constructor's extra_logs for other scenarios.
DEFAULT_LOG_PATHS = {
    "dcmanager": DCMANAGER_LOG,
    "state": STATE_LOG,
}

# dcmanager/state timestamp form: "YYYY-MM-DD HH:MM:SS" (UTC).
_TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


# dcmanager enroll phase model. Marker strings are the platform's own
# dcmanager/state log phrasing.
DCMANAGER_ENROLL_PHASES: List[KpiLogPhase] = [
    KpiLogPhase("create", "dcmanager", "Creating subcloud", "dcmanager", "Successfully created subcloud"),
    KpiLogPhase("pre_enroll", "dcmanager", "Successfully created subcloud", "dcmanager", "Start enroll init for"),
    KpiLogPhase("enroll_init", "dcmanager", "Start enroll init for", "dcmanager", "Starting enroll of subcloud"),
    KpiLogPhase("enroll", "dcmanager", "Starting enroll of subcloud", "dcmanager", "Successfully enrolled"),
    KpiLogPhase("enroll_deploy", "dcmanager", "Starting deploy of subcloud", "dcmanager", "Successfully deployed subcloud"),
    KpiLogPhase("reached_online", "dcmanager", "Successfully enrolled", "state", "availability:online", stop_pick="first"),
]


class DcManagerLogKpiKeywords(BaseKeyword):
    """Mine DC operation phase durations from the system controller logs."""

    def __init__(self, ssh_connection: SSHConnection, extra_logs: Optional[Dict[str, str]] = None):
        """Initialize with an SSH connection and an optional set of extra logs.

        Args:
            ssh_connection (SSHConnection): SSH to the active System Controller.
            extra_logs (Optional[Dict[str, str]]): Additional logical-log-name to
                absolute-path entries, merged with the dcmanager/state defaults so
                phases can reference other logs. A value overrides a default of the
                same name.
        """
        self.ssh_connection = ssh_connection
        self.log_paths = dict(DEFAULT_LOG_PATHS)
        if extra_logs:
            self.log_paths.update(extra_logs)

    def register_log(self, logical_name: str, path: str) -> None:
        """Register an extra logical-log-name to absolute-path mapping.

        Args:
            logical_name (str): Logical name a phase can reference.
            path (str): Absolute path to the log on the system controller.
        """
        self.log_paths[logical_name] = path

    def _resolve_log_path(self, logical_log: str) -> str:
        """Resolve a logical log name to its path, allowing a raw path fallback.

        Args:
            logical_log (str): Logical name, or an absolute path if not registered.

        Returns:
            str: The resolved log path.
        """
        return self.log_paths.get(logical_log, logical_log)

    def snapshot_log_line_count(self, logical_log: str = "dcmanager") -> int:
        """Return the current line count of a log, as a pre-operation anchor.

        Call this immediately before starting the operation. Pass the returned
        value as ``since_line`` to :meth:`mine_phase_durations` so only lines
        appended by this run are mined.

        Args:
            logical_log (str): Logical log name ('dcmanager' or 'state').

        Returns:
            int: Line count of the log now, or 0 if it cannot be read.
        """
        path = self._resolve_log_path(logical_log)
        # wc -l counts newlines, so a trailing partial line (one being written at
        # snapshot time) is not counted and could re-enter the mined slice. For the
        # dcmanager/state logs, which append whole lines, this is not a concern.
        output = self.ssh_connection.send_as_sudo_non_interactive(f"sh -c 'wc -l {path} 2>/dev/null || true'")
        text = "\n".join(output) if isinstance(output, list) else str(output)
        match = re.search(r"(\d+)", text)
        count = int(match.group(1)) if match else 0
        get_logger().log_info(f"Snapshot {logical_log} line count: {count}")
        return count

    def mine_phase_durations(
        self,
        subcloud_name: str,
        phases: List[KpiLogPhase],
        since_line: Optional[Dict[str, int]] = None,
    ) -> Dict[str, float]:
        """Mine each phase's duration (seconds) from the SC logs.

        For each phase, finds the start and stop marker lines (scoped to the
        target subcloud as an exact token, and to the lines appended after the
        pre-operation snapshot), parses their timestamps, and returns the delta.
        Phases whose markers are missing or produce a negative delta are omitted.
        A ``total`` key spanning the earliest start to the latest stop is added.

        Args:
            subcloud_name (str): Target subcloud (exact-token scoped).
            phases (List[KpiLogPhase]): Phase model to mine (e.g. DCMANAGER_ENROLL_PHASES).
            since_line (Optional[Dict[str, int]]): Per-logical-log line offsets from
                snapshot_log_line_count, so only this run's lines are considered.

        Returns:
            Dict[str, float]: phase name -> duration in seconds, plus 'total'.
        """
        since_line = since_line or {}
        durations: Dict[str, float] = {}
        starts: List[int] = []
        stops: List[int] = []

        for phase in phases:
            start_epoch = self._marker_epoch(phase.start_log, phase.start_marker, subcloud_name, phase.start_pick, since_line.get(phase.start_log, 0))
            stop_epoch = self._marker_epoch(phase.stop_log, phase.stop_marker, subcloud_name, phase.stop_pick, since_line.get(phase.stop_log, 0))

            if start_epoch is None or stop_epoch is None:
                get_logger().log_info(f"Phase '{phase.name}': marker(s) not found, skipping (start={start_epoch}, stop={stop_epoch})")
                continue

            delta = stop_epoch - start_epoch
            if delta < 0:
                get_logger().log_info(f"Phase '{phase.name}': negative duration ({delta}s), skipping")
                continue

            durations[phase.name] = float(delta)
            starts.append(start_epoch)
            stops.append(stop_epoch)
            get_logger().log_info(f"Phase '{phase.name}': {delta}s")

        if starts and stops:
            durations["total"] = float(max(stops) - min(starts))
            get_logger().log_info(f"Phase 'total': {durations['total']}s")

        return durations

    def _marker_epoch(self, logical_log: str, marker: str, subcloud_name: str, pick: str, since_line: int) -> Optional[int]:
        """Find a marker line for the subcloud and return its epoch seconds.

        Reads the log from ``since_line`` onward (this run only), keeps lines
        that contain the marker AND the subcloud as an exact token, then parses
        the timestamp of the first or last such line per ``pick``.

        Args:
            logical_log (str): Logical log name ('dcmanager'/'state').
            marker (str): Marker substring to match.
            subcloud_name (str): Subcloud name, matched as an exact token.
            pick (str): 'first' or 'last' matching line.
            since_line (int): 1-based line offset to start reading from.

        Returns:
            Optional[int]: Epoch seconds of the chosen line, or None.
        """
        path = self._resolve_log_path(logical_log)
        tail_from = since_line + 1 if since_line and since_line > 0 else 1
        # Read this run's slice of the log (root-only -> sudo). tail -n +N emits
        # from line N onward; grep narrows to the marker; the exact-token subcloud
        # filter prevents subcloud1 from matching subcloud11.
        line = self._read_marker_line(path, tail_from, marker, subcloud_name, pick)
        if not line:
            return None
        return self._line_to_epoch(line)

    def _read_marker_line(self, path: str, tail_from: int, marker: str, subcloud_name: str, pick: str) -> Optional[str]:
        """Return the first/last log line matching marker + subcloud token.

        Args:
            path (str): Absolute log path.
            tail_from (int): 1-based starting line (this run's slice).
            marker (str): Marker substring.
            subcloud_name (str): Exact-token subcloud filter.
            pick (str): 'first' or 'last'.

        Returns:
            Optional[str]: The matching line, or None if there is no match.
        """
        # Exact-token scoping: subcloud bounded by a non-alphanumeric character on
        # both sides so subcloud1 matches neither subcloud11 nor subcloud1a.
        sc_re = f"(^|[^A-Za-z0-9]){re.escape(subcloud_name)}([^A-Za-z0-9]|$)"
        selector = "tail -1" if pick == "last" else "head -1"
        marker_escaped = marker.replace("'", "'\\''")
        sc_re_escaped = sc_re.replace("'", "'\\''")
        pipeline = f"tail -n +{tail_from} {path} 2>/dev/null | grep -aF '{marker_escaped}' | grep -aE '{sc_re_escaped}' | {selector} || true"
        output = self.ssh_connection.send_as_sudo_non_interactive(f'sh -c "{pipeline}"')
        text = "\n".join(output) if isinstance(output, list) else str(output)
        text = text.strip()
        return text if text else None

    def _line_to_epoch(self, line: str) -> Optional[int]:
        """Parse a 'YYYY-MM-DD HH:MM:SS' UTC timestamp from a line to epoch seconds.

        Args:
            line (str): A log line.

        Returns:
            Optional[int]: Epoch seconds (UTC), or None if no timestamp is found.
        """
        match = _TS_RE.search(line)
        if not match:
            return None
        try:
            dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            return None
