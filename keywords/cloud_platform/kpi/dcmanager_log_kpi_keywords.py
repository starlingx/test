"""Mine DC operation phase durations from platform logs.

Each phase is bounded by a start and stop marker that the platform already
writes; a phase duration is the difference between those two log timestamps
(platform-truth, not the test's wall clock). Only this run's lines are mined:
the caller passes ``since_line`` from a pre-operation snapshot
(``snapshot_log_line_count``) or from an after-the-fact anchor
(``anchor_since_last_session``). Logs are root-only, so reads use sudo.

The dcmanager, state and fm-manager logs are registered by default; other logs
can be added per instance (constructor ``extra_logs`` or ``register_log``) so the
same miner serves operations whose markers live in different logs. The
fm-manager log is read on the subcloud when a subcloud connection is given.
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
# Subcloud log (root-only) holding the alarm set/clear timeline.
FM_MANAGER_LOG = "/var/log/fm-manager.log"

# Per-subcloud ansible playbook output dcmanager writes on the system controller.
# The path depends on the subcloud, so register it as "ansible" via extra_logs.
ANSIBLE_PLAYBOOK_LOG_TEMPLATE = "/var/log/dcmanager/ansible/{subcloud_name}_playbook_output.log"

# Default logical log name -> absolute path, matching the phase "log" token.
DEFAULT_LOG_PATHS = {
    "dcmanager": DCMANAGER_LOG,
    "state": STATE_LOG,
    "fmmanager": FM_MANAGER_LOG,
}

# Logs that live on the subcloud, read over the subcloud connection.
_SUBCLOUD_HOST_LOGS = ("fmmanager",)
# Logs holding only one subcloud's lines, so the subcloud-name filter is skipped.
_UNSCOPED_LOGS = ("ansible", "fmmanager")
# Ansible playbook logs: logrotate can rename them mid-operation while ansible
# keeps writing to the open (now ".1") file, so they are read as "<path>.1" then
# "<path>". Their TASK headers carry no timestamp; the time is on the next line.
_ANSIBLE_LOGS = ("ansible",)

# "YYYY-MM-DD HH:MM:SS" (dcmanager/state), "YYYY-MM-DDTHH:MM:SS" (fm-manager) and
# "YYYY-MM-DD-HH:MM:SS" (dcmanager ansible log); all UTC.
_TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[ T-](\d{2}:\d{2}:\d{2})")
# ansible profile_tasks form: "Tuesday 10 November 2026  17:36:59 +0000".
_PROFILE_TS_RE = re.compile(r"[A-Z][a-z]+ (\d{1,2} [A-Z][a-z]+ \d{4}) +(\d{2}:\d{2}:\d{2}) \+0000")


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


def _ansible_phase(name: str, start_marker: str, stop_marker: str) -> KpiLogPhase:
    """Build a phase bounded by two markers in the SC ansible playbook log.

    Args:
        name (str): Phase name.
        start_marker (str): Regex marking the phase start (first match).
        stop_marker (str): Regex marking the phase stop (first match).

    Returns:
        KpiLogPhase: The phase.
    """
    return KpiLogPhase(name, "ansible", start_marker, "ansible", stop_marker, start_pick="first", stop_pick="first", regex=True)


# Fixed substring of the "Executing playbook command" line that starts a subcloud
# restore in the SC ansible log; anchors onsite-restore mining to the last restore.
ONSITE_RESTORE_SESSION_MARKER = "playbooks/restore_subcloud_backup.yml', '-i'"

# Onsite restore markers: task headers of restore_subcloud_backup.yml taken from a
# real onsite restore. Anchored to line start because the log also carries the
# subcloud's own playbook output inside a single "msg" line with TASK/RECAP text.
_RESTORE_PLAYBOOK_START = r"Executing playbook command.*restore_subcloud_backup\.yml"
_TASK_PATCH_BEFORE_RESTORE = r"^TASK \[Patch the subcloud to the backup level before restore\]"
_TASK_RESTORE_OVERRIDES = r"^TASK \[common/prepare-and-transfer-subcloud-overrides : "
_TASK_PLATFORM_RESTORE = r"^TASK \[subcloud-bnr/restore : Get system controller oam ip\]"
_TASK_HOST_UNLOCK = r"^TASK \[Perform host unlock\]"
_TASK_RESTORE_COMPLETE = r"^TASK \[subcloud-bnr/restore : Run system restore-complete\]"
_TASKS_RECAP = r"^TASKS RECAP"

# On-site restore (without reinstall) phase model. The system controller drives the
# standard subcloud restore (restore_subcloud_backup.yml), so the phases are mined
# from the subcloud's ansible playbook log on the SC, anchored at the last
# ONSITE_RESTORE_SESSION_MARKER. Phases are contiguous, so 'total' is the
# end-to-end span:
#   restore_prepare      prechecks, prepare-env, connectivity, input validation
#   patch_before_restore re-apply the backup's patches (no-op when none)
#   restore_overrides    prepare and transfer the restore overrides
#   platform_restore     backup transfer, subcloud platform restore playbook, OAM
#                        reconfig, cleanup
#   host_unlock          unlock controller-0 and wait for it to recover
#   restore_complete     system restore-complete to end of playbook
#   alarm_clear          end of playbook to the last alarm clear in the subcloud
#                        fm-manager.log. Mined after the test's health check
#                        (alarms clear), so the last clear is the clear moment.
ONSITE_RESTORE_PHASES: List[KpiLogPhase] = [
    _ansible_phase("restore_prepare", _RESTORE_PLAYBOOK_START, _TASK_PATCH_BEFORE_RESTORE),
    _ansible_phase("patch_before_restore", _TASK_PATCH_BEFORE_RESTORE, _TASK_RESTORE_OVERRIDES),
    _ansible_phase("restore_overrides", _TASK_RESTORE_OVERRIDES, _TASK_PLATFORM_RESTORE),
    _ansible_phase("platform_restore", _TASK_PLATFORM_RESTORE, _TASK_HOST_UNLOCK),
    _ansible_phase("host_unlock", _TASK_HOST_UNLOCK, _TASK_RESTORE_COMPLETE),
    _ansible_phase("restore_complete", _TASK_RESTORE_COMPLETE, _TASKS_RECAP),
    KpiLogPhase("alarm_clear", "ansible", _TASKS_RECAP, "fmmanager", r"Deleted alarm\(s\):", start_pick="first", stop_pick="last", regex=True),
]


class DcManagerLogKpiKeywords(BaseKeyword):
    """Mine DC operation phase durations from platform logs."""

    def __init__(self, ssh_connection: SSHConnection, extra_logs: Optional[Dict[str, str]] = None):
        """Initialize with an SSH connection and an optional set of extra logs.

        Args:
            ssh_connection (SSHConnection): SSH to the active System Controller.
            extra_logs (Optional[Dict[str, str]]): Additional logical-log-name to
                absolute-path entries, merged with the defaults so phases can
                reference other logs. A value overrides a default of the same name.
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

    def _log_source(self, logical_log: str) -> str:
        """Return a shell command that streams a log's lines.

        Ansible logs are streamed as the previous rotation followed by the current
        file, so a rotation during the operation doesn't hide its lines.

        Args:
            logical_log (str): Logical log name.

        Returns:
            str: Shell command writing the log lines to stdout.
        """
        path = self._resolve_log_path(logical_log)
        if logical_log in _ANSIBLE_LOGS:
            return f"cat {path}.1 {path} 2>/dev/null"
        return f"cat {path} 2>/dev/null"

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

    def anchor_since_last_session(self, logical_log: str, session_marker: str) -> Dict[str, int]:
        """Return a ``since_line`` anchored at the last occurrence of a session marker.

        Used when a pre-operation line snapshot is not reliable: the log may be
        rotated during the operation, and it may carry earlier operations' lines.
        The current operation begins at the last ``session_marker``; without one,
        the whole log is mined.

        Args:
            logical_log (str): Logical log name whose session to anchor (e.g. 'ansible').
            session_marker (str): Fixed substring that begins each operation run
                (e.g. ONSITE_RESTORE_SESSION_MARKER).

        Returns:
            Dict[str, int]: ``{logical_log: anchor_line}`` to pass as ``since_line``;
                ``anchor_line`` is one less than the marker's line so the marker
                itself is included in the mined slice. Empty dict if no marker.
        """
        marker_escaped = session_marker.replace("'", "'\\''")
        pipeline = f"{self._log_source(logical_log)} | grep -aFn '{marker_escaped}' | tail -1 || true"
        output = self.ssh_connection.send_as_sudo_non_interactive(f'sh -c "{pipeline}"')
        text = "\n".join(output) if isinstance(output, list) else str(output)
        match = re.search(r"^(\d+):", text, re.MULTILINE)
        if not match:
            get_logger().log_info(f"No '{session_marker}' marker in {logical_log}; mining whole log")
            return {}
        anchor = int(match.group(1)) - 1
        get_logger().log_info(f"Anchoring {logical_log} at line {anchor} (last session start marker on line {anchor + 1})")
        return {logical_log: anchor}

    def mine_phase_durations(
        self,
        subcloud_name: str,
        phases: List[KpiLogPhase],
        since_line: Optional[Dict[str, int]] = None,
        subcloud_ssh: Optional[SSHConnection] = None,
    ) -> Dict[str, float]:
        """Mine each phase's duration (seconds) from the logs.

        For each phase, finds the start and stop marker lines (scoped to the
        target subcloud, and to the lines after ``since_line``), parses their
        timestamps, and returns the delta. Markers in a subcloud-side log
        (fm-manager) are read over ``subcloud_ssh``; a phase that needs one is
        skipped when no subcloud connection is given. Phases whose markers are
        missing or produce a negative delta are omitted. A ``total`` key spanning
        the earliest start to the latest stop is added.

        Args:
            subcloud_name (str): Target subcloud (exact-token scoped on shared logs).
            phases (List[KpiLogPhase]): Phase model to mine (e.g. DCMANAGER_ENROLL_PHASES).
            since_line (Optional[Dict[str, int]]): Per-logical-log line offsets, so
                only this run's lines are considered.
            subcloud_ssh (Optional[SSHConnection]): SSH to the subcloud, for phases
                whose markers are in a subcloud-side log.

        Returns:
            Dict[str, float]: phase name -> duration in seconds, plus 'total'.
        """
        since_line = since_line or {}
        durations: Dict[str, float] = {}
        starts: List[int] = []
        stops: List[int] = []

        for phase in phases:
            if subcloud_ssh is None and (phase.start_log in _SUBCLOUD_HOST_LOGS or phase.stop_log in _SUBCLOUD_HOST_LOGS):
                get_logger().log_info(f"Phase '{phase.name}': needs a subcloud log and no subcloud connection, skipping")
                continue
            start_epoch = self._marker_epoch(phase.start_log, phase.start_marker, subcloud_name, phase.start_pick, since_line.get(phase.start_log, 0), phase.regex, subcloud_ssh)
            stop_epoch = self._marker_epoch(phase.stop_log, phase.stop_marker, subcloud_name, phase.stop_pick, since_line.get(phase.stop_log, 0), phase.regex, subcloud_ssh)

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

    def _marker_epoch(self, logical_log: str, marker: str, subcloud_name: str, pick: str, since_line: int, regex: bool, subcloud_ssh: Optional[SSHConnection]) -> Optional[int]:
        """Find a marker line and return its epoch seconds.

        Reads the log from ``since_line`` onward (this run only) on the host that
        holds it, keeps lines that match the marker (and, on shared logs, the
        subcloud as an exact token), then parses the timestamp of the first or last
        such line per ``pick``. For ansible logs the line after the marker is kept
        too, since it carries the task's timestamp.

        Args:
            logical_log (str): Logical log name.
            marker (str): Marker to match (fixed substring, or regex if regex=True).
            subcloud_name (str): Subcloud name, matched as an exact token on shared logs.
            pick (str): 'first' or 'last' matching line.
            since_line (int): Number of leading lines to skip (this run's slice).
            regex (bool): Match the marker with grep -E (regex) vs grep -F (fixed).
            subcloud_ssh (Optional[SSHConnection]): SSH to the subcloud, used for
                subcloud-side logs.

        Returns:
            Optional[int]: Epoch seconds of the chosen line, or None.
        """
        connection = subcloud_ssh if logical_log in _SUBCLOUD_HOST_LOGS and subcloud_ssh is not None else self.ssh_connection
        ansible = logical_log in _ANSIBLE_LOGS
        marker_escaped = marker.replace("'", "'\\''")
        grep_flags = ("-aE" if regex else "-aF") + (" -A1" if ansible else "")

        pipeline = f"{self._log_source(logical_log)} | tail -n +{since_line + 1} | grep {grep_flags} '{marker_escaped}'"
        if ansible:
            # Drop grep's '--' group separators between marker/next-line pairs.
            pipeline += " | grep -avx -e '--'"
        if logical_log not in _UNSCOPED_LOGS:
            # Exact-token scoping so subcloud1 matches neither subcloud11 nor subcloud1a.
            sc_re = f"(^|[^A-Za-z0-9]){re.escape(subcloud_name)}([^A-Za-z0-9]|$)".replace("'", "'\\''")
            pipeline += f" | grep -aE '{sc_re}'"
        lines = 2 if ansible else 1
        pipeline += f" | {'tail' if pick == 'last' else 'head'} -{lines} || true"

        output = connection.send_as_sudo_non_interactive(f'sh -c "{pipeline}"')
        text = ("\n".join(output) if isinstance(output, list) else str(output)).strip()
        return self._line_to_epoch(text) if text else None

    def _line_to_epoch(self, line: str) -> Optional[int]:
        """Parse a UTC timestamp from a log line (or marker + next line) to epoch seconds.

        Accepts 'YYYY-MM-DD HH:MM:SS' with a space, 'T' or '-' separator, and the
        ansible profile_tasks form 'Tuesday 10 November 2026  17:36:59 +0000'.

        Args:
            line (str): A log line, or a marker line joined with its next line.

        Returns:
            Optional[int]: Epoch seconds (UTC), or None if no timestamp is found.
        """
        match = _TS_RE.search(line)
        fmt = "%Y-%m-%d %H:%M:%S"
        if not match:
            match = _PROFILE_TS_RE.search(line)
            fmt = "%d %B %Y %H:%M:%S"
        if not match:
            return None
        try:
            return int(datetime.strptime(f"{match.group(1)} {match.group(2)}", fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            return None
