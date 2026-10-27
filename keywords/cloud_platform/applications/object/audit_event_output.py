"""Correlate interpreted ausearch records from a single node."""

import re
from shlex import split

from framework.exceptions.keyword_exception import KeywordException

# libaudit parses auditd.conf when any audit tool starts and reports unusable or
# superseded settings on its own output. The shipped chart configuration triggers
# these on supported releases, so they arrive alongside real records. They describe
# the daemon configuration, never an audited action, and must not be read as
# evidence; anything else unrecognized still fails. Callers report the collected
# diagnostics; this object stays free of logging configuration.
_DIAGNOSTICS = (
    re.compile(r"^The (?:disp_qos|dispatcher) option is deprecated - line \d+$"),
    re.compile(r"^Skipping line \d+ in /etc/audit/auditd\.conf: too long$"),
)


class AuditEventOutput:
    """Keep records grouped by audit event ID rather than joining unrelated evidence."""

    def __init__(self, text: str, return_code: int = 0) -> None:
        """Validate command status and parse audit records or an explicit empty result.

        Args:
            text (str): Combined command output, including kubectl diagnostics.
            return_code (int): Exit status of the pod exec command.
        """
        if return_code not in (0, 1):
            raise KeywordException(f"Audit search failed with status {return_code}: {text}")
        self.events = {}
        self.diagnostics = []
        no_matches = False
        for line in text.splitlines():
            line = line.strip()
            if not line or line == "----" or line.startswith("time->"):
                continue
            # kubectl reports a nonzero container exit on stderr alongside ausearch.
            # This trailer alone never establishes an empty search result.
            if return_code == 1 and line == "command terminated with exit code 1":
                continue
            if line == "<no matches>":
                no_matches = True
                continue
            if any(pattern.fullmatch(line) for pattern in _DIAGNOSTICS):
                self.diagnostics.append(line)
                continue
            match = re.fullmatch(r"(?:node=(\S+)\s+)?type=(\w+)\s+msg=audit\(([^)]+)\)\s*:\s*(.*)", line)
            if not match:
                raise KeywordException(f"Malformed audit event evidence: {line!r}")
            node, record_type, event_id, content = match.groups()
            try:
                fields = dict(token.split("=", 1) for token in split(content) if "=" in token)
            except ValueError as error:
                raise KeywordException(f"Malformed audit event fields: {line!r}") from error
            self.events.setdefault((node, event_id), []).append((record_type, fields))
        if return_code == 1 and not no_matches:
            raise KeywordException(f"Audit search failed with status {return_code}: {text}")
        if no_matches and self.events:
            raise KeywordException("Audit output contains both records and a no-match marker")

    def successful_rmdir_event(self, key: str, path: str) -> str | None:
        """Find one successful rmdir with the exact key and deleted path in the same event.

        Args:
            key (str): Unique runtime rule key for this action.
            path (str): Absolute directory path removed by the action.

        Returns:
            str | None: Matching audit event ID, or None while evidence is incomplete.
        """
        for (_, event_id), records in self.events.items():
            syscall = any(kind == "SYSCALL" and fields.get("syscall") == "rmdir" and fields.get("success") == "yes" and fields.get("exit") == "0" and fields.get("key") == key for kind, fields in records)
            deleted_path = any(kind == "PATH" and fields.get("name") == path and fields.get("nametype") == "DELETE" for kind, fields in records)
            if syscall and deleted_path:
                return event_id
        return None
