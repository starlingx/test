"""Fresh-event correlation, cleanup and real shell-command failure contracts."""

import subprocess
from pathlib import Path
from shlex import split
from types import SimpleNamespace
from unittest.mock import MagicMock, NonCallableMagicMock, patch

import pytest

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.applications.auditd_keywords import AuditdKeywords
from keywords.cloud_platform.applications.object.audit_event_output import AuditEventOutput
from keywords.cloud_platform.upgrade.audit_event_capture_keywords import AuditEventCaptureKeywords


def event(key: str, path: str, serial: str = "123", success: str = "yes", syscall: str = "rmdir", exit_code: str = "0") -> str:
    """Build interpreted records matching ausearch's default output format.

    Args:
        key (str): Rule key.
        path (str): Deleted directory.
        serial (str): Event serial.
        success (str): Syscall success field.
        syscall (str): Interpreted syscall name.
        exit_code (str): Syscall exit status.

    Returns:
        str: Ausearch records.
    """
    identity = f"10/19/2026 14:30:00.123:{serial}"
    return f'----\ntime->Mon Oct 19 14:30:00 2026\ntype=PATH msg=audit({identity}) : item=0 name={path} nametype=DELETE\ntype=SYSCALL msg=audit({identity}) : arch=x86_64 syscall={syscall} success={success} exit={exit_code} key="{key}"\n'


@pytest.mark.parametrize("change", [{"key": "stale"}, {"path": "/tmp/other"}, {"success": "no"}, {"syscall": "mkdir"}, {"exit_code": "-1"}])
def test_reject_unrelated_or_failed_events(change: dict) -> None:
    """Reject old keys, wrong paths, unsuccessful actions and other syscalls.

    Args:
        change (dict): Field changed from a valid event.
    """
    values = {"key": "fresh", "path": "/tmp/fresh", **change}
    assert AuditEventOutput(event(**values)).successful_rmdir_event("fresh", "/tmp/fresh") is None


def test_require_same_event_id() -> None:
    """Do not combine a matching syscall and path from two different events."""
    text = event("fresh", "/tmp/other", "1") + event("other", "/tmp/fresh", "2")
    assert AuditEventOutput(text).successful_rmdir_event("fresh", "/tmp/fresh") is None


def test_require_same_node_identity() -> None:
    """Identical serials from different nodes must not combine into a matching event."""
    records = [line for line in event("fresh", "/tmp/fresh").splitlines() if line.startswith("type=")]
    text = f"node=worker-0 {records[0]}\nnode=controller-0 {records[1]}"
    assert AuditEventOutput(text).successful_rmdir_event("fresh", "/tmp/fresh") is None


def test_require_deleted_path_and_syscall() -> None:
    """Reject a parent path, missing syscall and missing path records."""
    text = event("fresh", "/tmp/fresh")
    for changed in (text.replace("DELETE", "PARENT"), "\n".join(line for line in text.splitlines() if "type=PATH" not in line), "\n".join(line for line in text.splitlines() if "type=SYSCALL" not in line)):
        assert AuditEventOutput(changed).successful_rmdir_event("fresh", "/tmp/fresh") is None


@pytest.mark.parametrize("text", ["", "\n", "----\n"])
def test_empty_evidence_is_pending(text: str) -> None:
    """Empty output never proves event capture.

    Args:
        text (str): Empty observation.
    """
    assert AuditEventOutput(text).successful_rmdir_event("fresh", "/tmp/fresh") is None


@pytest.mark.parametrize("text", ["connection refused", "type=PATH msg=broken", 'type=PATH msg=audit(123:1): name="unterminated'])
def test_bad_evidence_fails_explicitly(text: str) -> None:
    """Do not turn command diagnostics or corrupt records into success.

    Args:
        text (str): Malformed evidence.
    """
    with pytest.raises(KeywordException):
        AuditEventOutput(text)


def test_positive_correlation() -> None:
    """Find the event ID in either record order, allowing a node prefix."""
    text = event("fresh", "/tmp/fresh")
    assert AuditEventOutput(text).successful_rmdir_event("fresh", "/tmp/fresh").endswith(":123")
    lines = [f"node=controller-0 {line}" for line in text.splitlines() if line.startswith("type=")]
    assert AuditEventOutput("\n".join(reversed(lines))).successful_rmdir_event("fresh", "/tmp/fresh").endswith(":123")


# Observed on the 26.03 lab: the shipped chart configuration makes libaudit report
# superseded and oversized settings on every audit tool invocation.
LAB_DIAGNOSTICS = "The disp_qos option is deprecated - line 16\nThe dispatcher option is deprecated - line 17\nSkipping line 38 in /etc/audit/auditd.conf: too long\n"


def test_configuration_diagnostics_do_not_hide_a_real_event() -> None:
    """Keep correlating records when audit tools report configuration diagnostics."""
    output = AuditEventOutput(LAB_DIAGNOSTICS + event("fresh", "/tmp/fresh"))
    assert output.successful_rmdir_event("fresh", "/tmp/fresh").endswith(":123")
    assert len(output.diagnostics) == 3


def test_configuration_diagnostics_alone_remain_pending() -> None:
    """Diagnostics without records are not evidence that an action was audited."""
    output = AuditEventOutput(LAB_DIAGNOSTICS)
    assert output.successful_rmdir_event("fresh", "/tmp/fresh") is None
    assert output.events == {}


@pytest.mark.parametrize(
    "text",
    [
        "The disp_qos option is unsupported - line 16",
        "Skipping line 38",
        "ausearch: unknown option",
        "The option is deprecated - line 16",
        "The unrelated option is deprecated - line 16",
        "Skipping line 38 in /etc/audit/auditd.conf: permission denied",
        "Skipping line 38 in /tmp/other.conf: too long",
    ],
)
def test_unknown_non_record_lines_still_fail(text: str) -> None:
    """Only the known configuration diagnostics are tolerated.

    Args:
        text (str): Line that does not match a record or a known diagnostic.
    """
    with pytest.raises(KeywordException):
        AuditEventOutput(text)


class AuditNodeModel(AuditdKeywords):
    """Model action-dependent evidence on separate nodes without mocking validation."""

    def __init__(self):
        self.ssh_connection = NonCallableMagicMock()
        self.ssh_connection.get_return_code.return_value = 0
        self.rules = {"controller-0": ["user-rule"], "worker-0": ["worker-rule"]}
        self.original_rules = {node: list(rules) for node, rules in self.rules.items()}
        self.paths = {node: set() for node in self.rules}
        self.records = {node: "" for node in self.rules}
        self.calls = []
        self.pending = 0
        self.fail_action = False
        self.fail_add_reply = False
        self.fail_mkdir_reply = False
        self.fail_delete = False
        self.drop_events = False

    def verify_runtime(self, hosts):
        """Require the same full inventory before generating actions."""
        assert set(hosts) == set(self.rules)
        self.calls.append(("runtime", hosts))

    def node_command(self, hostname, command):
        """Create and remove paths; only an installed rule produces evidence."""
        self.calls.append((hostname, command))
        args = split(command)
        if args[0] == "mkdir":
            self.paths[hostname].add(args[-1])
            if self.fail_mkdir_reply:
                raise KeywordException("directory created but response lost")
        elif args[0] == "rmdir":
            if self.fail_action:
                raise KeywordException("host action failed")
            self.paths[hostname].remove(args[-1])
            if len(self.rules[hostname]) == 2 and not self.drop_events:
                key = split(self.rules[hostname][0])[-1]
                self.records[hostname] = event(key, args[-1])
        elif args[:2] == ["sh", "-c"]:
            self.paths[hostname].clear()
        else:
            raise AssertionError(command)
        return ""

    def pod_command(self, hostname, hosts, command, ignore_error=False):
        """Manage exact rules and return only the selected node's audit evidence."""
        assert hostname in hosts
        self.calls.append((hostname, command))
        args = split(command)
        if args[:2] == ["auditctl", "-A"]:
            self.rules[hostname].insert(0, " ".join(args[2:]))
            if self.fail_add_reply:
                raise KeywordException("rule installed but response lost")
        elif args[:2] == ["auditctl", "-l"]:
            return "\n".join(self.rules[hostname])
        elif args[:2] == ["auditctl", "-d"]:
            if self.fail_delete:
                raise KeywordException("rule delete failed")
            self.rules[hostname].remove(" ".join(args[2:]))
        elif args[:3] == ["env", "LC_ALL=C", "ausearch"]:
            assert ignore_error
            assert "--input-logs" in args and args[-2:] == ["-sc", "rmdir"]
            if self.pending:
                self.pending -= 1
                return ""
            return self.records[hostname]
        else:
            raise AssertionError(command)
        return ""


@pytest.fixture(autouse=True)
def base_logger():
    """Keep framework command tracing independent of lab logger configuration."""
    with patch("keywords.base_keyword.get_logger"):
        yield


@pytest.fixture
def capture():
    """Build the real capture keyword with a node model at its command boundary."""
    kw = AuditEventCaptureKeywords.__new__(AuditEventCaptureKeywords)
    kw.audit = AuditNodeModel()
    with patch("keywords.cloud_platform.upgrade.audit_event_capture_keywords.get_logger"), patch("keywords.cloud_platform.applications.auditd_keywords.get_logger"), patch("framework.validation.validation.get_logger"), patch("framework.validation.validation.sleep"):
        yield kw


def test_all_nodes_phases_and_cleanup(capture):
    """Exercise all phases with delayed evidence and independently owned finalizers."""
    finalizers = []
    request = SimpleNamespace(addfinalizer=finalizers.append)
    capture.audit.pending = 2
    for phase in ("pre", "post-upgrade", "post-rollback"):
        capture.validate_event_capture(request, phase, tuple(capture.audit.rules))
        assert capture.audit.rules == capture.audit.original_rules
        assert not any(capture.audit.paths.values())
    keys = [split(command)[-1] for _, command in capture.audit.calls if isinstance(command, str) and command.startswith("auditctl -A")]
    assert len(keys) == len(set(keys)) == 6
    assert all(len(key) < 31 for key in keys)
    assert len(finalizers) == 6
    calls = list(capture.audit.calls)
    for finalizer in reversed(finalizers):
        finalizer()
    assert capture.audit.calls == calls


@pytest.mark.parametrize("failure", ["fail_action", "fail_add_reply", "fail_mkdir_reply"])
def test_partial_failure_cleanup(capture: AuditEventCaptureKeywords, failure: str) -> None:
    """Recover artifacts even when rule installation succeeds but its reply fails.

    Args:
        capture (AuditEventCaptureKeywords): Capture keyword with an in-memory command model.
        failure (str): Failure injected before event collection.
    """
    finalizers = []
    setattr(capture.audit, failure, True)
    with pytest.raises(KeywordException):
        capture.validate_event_capture(SimpleNamespace(addfinalizer=finalizers.append), "pre", tuple(capture.audit.rules))
    assert len(finalizers) == 1
    for finalizer in reversed(finalizers):
        finalizer()
    assert capture.audit.rules == capture.audit.original_rules
    assert not any(capture.audit.paths.values())


def test_cleanup_failure_keeps_retry_and_cleans_path(capture):
    """One failed cleanup stage must not abandon the independent path cleanup."""
    capture.audit.fail_action = True
    capture.audit.fail_delete = True
    finalizers = []
    with pytest.raises(KeywordException):
        capture.validate_event_capture(SimpleNamespace(addfinalizer=finalizers.append), "pre", tuple(capture.audit.rules))
    with pytest.raises(ExceptionGroup, match="artifact cleanup"):
        finalizers[0]()
    assert not any(capture.audit.paths.values())
    capture.audit.fail_delete = False
    finalizers[0]()
    assert capture.audit.rules == capture.audit.original_rules


def test_event_timeout_and_cleanup(capture):
    """Missing fresh evidence fails within the polling budget and remains recoverable."""
    capture.audit.drop_events = True
    finalizers = []
    with patch("framework.validation.validation.time.time", side_effect=[0, 121]):
        with pytest.raises(KeywordException, match="Timed out.*controller-0"):
            capture.validate_event_capture(SimpleNamespace(addfinalizer=finalizers.append), "pre", tuple(capture.audit.rules))
    finalizers[0]()
    assert capture.audit.rules == capture.audit.original_rules


@pytest.mark.parametrize("hosts", [(), ("controller-0", "controller-0")])
def test_bad_inventory(capture: AuditEventCaptureKeywords, hosts: tuple[str, ...]) -> None:
    """Never pass an empty or duplicate-node inventory.

    Args:
        capture (AuditEventCaptureKeywords): Capture keyword with an in-memory command model.
        hosts (tuple[str, ...]): Invalid node inventory.
    """
    with pytest.raises(ValueError):
        capture.validate_event_capture(MagicMock(), "pre", hosts)


@pytest.mark.parametrize(
    "status,output,accepted",
    [
        (1, "<no matches>", True),
        (1, "permission denied", False),
        (127, "ausearch: not found", False),
        (1, "", False),
        (0, "", True),
        # The lab emits configuration diagnostics alongside the marker, so the
        # no-match signal has to be recognized as a line rather than as the
        # whole output; otherwise "not recorded yet" is reported as a failure.
        (1, "The disp_qos option is deprecated - line 16\n<no matches>", True),
        (0, "The disp_qos option is deprecated - line 16", True),
        (1, "The disp_qos option is deprecated - line 16\nno matches", False),
        (1, LAB_DIAGNOSTICS + "<no matches>", True),
        (1, "<no matches>\n" + LAB_DIAGNOSTICS, True),
        (1, "permission denied\n<no matches>", False),
        (1, "<no matches>\npermission denied", False),
        (1, "ausearch: failed to open <no matches>", False),
        (1, "prefix<no matches>", False),
        (1, "<no matches>suffix", False),
        (2, "<no matches>", False),
        (127, "<no matches>", False),
        (1, "Skipping line 38 in /etc/audit/auditd.conf: permission denied\n<no matches>", False),
        (1, event("key", "/tmp/fresh") + "<no matches>", False),
        (0, event("key", "/tmp/fresh") + "<no matches>", False),
    ],
)
def test_search_output_and_status_contract(tmp_path: Path, status: int, output: str, accepted: bool):
    """Execute the search command and pass its output/status to the real parser.

    Args:
        tmp_path (Path): Temporary command directory.
        status (int): Ausearch exit status.
        output (str): Ausearch output.
        accepted (bool): Whether the output parser should accept the result.
    """
    tool = tmp_path / "ausearch"
    tool.write_text(f"#!/bin/sh\nprintf '%s\\n' '{output}' >&2\nexit {status}\n")
    tool.chmod(0o700)
    kw = AuditdKeywords.__new__(AuditdKeywords)
    kw.ssh_connection = NonCallableMagicMock()

    def run_script(hostname, hosts, command, ignore_error=False):
        assert ignore_error
        result = subprocess.run(split(command), env={"PATH": f"{tmp_path}:/usr/bin:/bin"}, capture_output=True, text=True, check=False)
        kw.ssh_connection.get_return_code.return_value = result.returncode
        trailer = f"command terminated with exit code {result.returncode}\n" if result.returncode else ""
        return result.stdout + result.stderr + trailer

    kw.pod_command = run_script
    # search_syscall_events reports ignored configuration diagnostics; the framework
    # logger is configured by a real run, not by this isolated unit test.
    with patch("keywords.cloud_platform.applications.auditd_keywords.get_logger"):
        if accepted:
            result = kw.search_syscall_events("controller-0", ("controller-0",), "key", "rmdir")
            assert result.events == {}
            if "disp_qos" in output:
                assert result.diagnostics
        else:
            with pytest.raises(KeywordException):
                kw.search_syscall_events("controller-0", ("controller-0",), "key", "rmdir")


@pytest.mark.parametrize("readiness", [False, True])
def test_audit_discovery_retries_failed_read_without_accepting_empty_evidence(readiness: bool) -> None:
    """Retry both direct discovery and readiness after a transient Kubernetes outage.

    Args:
        readiness (bool): Whether the caller also validates pod readiness.
    """
    audit = AuditdKeywords.__new__(AuditdKeywords)
    audit.ssh_connection = NonCallableMagicMock()
    audit.kubeconfig_path = "/etc/kubernetes/admin.conf"
    audit.ssh_connection.send.side_effect = ["The connection to the server was refused", '{"items": []}']
    audit.ssh_connection.get_return_code.side_effect = [1, 0]
    with patch("keywords.base_keyword.get_logger"), patch("keywords.cloud_platform.applications.auditd_keywords.get_logger"), patch("keywords.k8s.pods.kubectl_get_pods_keywords.get_logger"), patch("keywords.k8s.pods.kubectl_get_pods_keywords.time.sleep") as sleep:
        if readiness:
            assert audit.ready_pods(("controller-0",)) == {}
        else:
            assert audit.discover_pods() == []
    assert audit.ssh_connection.send.call_count == 2
    sleep.assert_called_once_with(10)
    assert all("-l app=auditd -o json" in call.args[0] for call in audit.ssh_connection.send.call_args_list)


def test_audit_discovery_fails_when_pod_reads_never_recover() -> None:
    """Exhausted API retries remain a failure rather than successful empty evidence."""
    audit = AuditdKeywords.__new__(AuditdKeywords)
    audit.ssh_connection = NonCallableMagicMock()
    audit.kubeconfig_path = "/etc/kubernetes/admin.conf"
    audit.ssh_connection.send.return_value = "The connection to the server was refused"
    audit.ssh_connection.get_return_code.return_value = 1
    with patch("keywords.base_keyword.get_logger"), patch("keywords.cloud_platform.applications.auditd_keywords.get_logger"), patch("keywords.k8s.pods.kubectl_get_pods_keywords.get_logger"), patch("keywords.k8s.pods.kubectl_get_pods_keywords.time.sleep"), patch("keywords.k8s.pods.kubectl_get_pods_keywords.time.time", side_effect=[0, 0, 61]):
        with pytest.raises(KeywordException, match="Could not read the pod list"):
            audit.ready_pods(("controller-0",))
    audit.ssh_connection.send.assert_called_once()
