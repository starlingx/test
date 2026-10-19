"""Audit helper failure modes exercised without lab access."""

import copy
import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, NonCallableMagicMock, patch
from uuid import uuid4

import pytest

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.cloud_platform.applications.auditd_keywords import AuditdKeywords, parse_audit_config, wait_for_audit
from keywords.cloud_platform.applications.auditd_state import AuditdBaseline, AuditdState
from keywords.k8s.k8s_command_wrapper import K8sConfigExporter

HOSTS = ("controller-0", "worker-0")


def pod(host: str, uid: str = "old") -> dict:
    """Build Kubernetes evidence with all readiness fields.

    Args:
        host (str): Node for the pod.
        uid (str): Pod identity.

    Returns:
        dict: Pod JSON record.
    """
    return {
        "metadata": {"name": f"auditd-{host}", "uid": uid},
        "spec": {"nodeName": host, "containers": [{"name": "auditd"}]},
        "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}], "containerStatuses": [{"name": "auditd", "ready": True, "restartCount": 0, "state": {"running": {}}}]},
    }


def register_connection(connection: NonCallableMagicMock) -> NonCallableMagicMock:
    """Register a fake connection through the same ownership map as the factory.

    Args:
        connection (NonCallableMagicMock): Fake connection returned by the factory.

    Returns:
        NonCallableMagicMock: Registered connection.
    """
    SSHConnectionManager.ssh_connection_list[connection.get_name()] = connection
    return connection


def managed_connection() -> NonCallableMagicMock:
    """Create a fake SSH connection owned by the framework manager.

    Returns:
        NonCallableMagicMock: Registered fake connection with a unique name.
    """
    connection = NonCallableMagicMock()
    connection.get_name.return_value = f"audit-unit-{uuid4().hex}"
    return register_connection(connection)


@pytest.fixture(autouse=True)
def audit_loggers() -> Generator[None, None, None]:
    """Keep helper tests independent of lab logging configuration.

    Yields:
        None: Patched framework and audit loggers.
    """
    with patch("keywords.base_keyword.get_logger"), patch("framework.validation.validation.get_logger"), patch("keywords.cloud_platform.applications.auditd_keywords.get_logger"), patch("keywords.cloud_platform.applications.auditd_state.get_logger"), patch.dict(SSHConnectionManager.ssh_connection_list, clear=True):
        yield


@pytest.fixture
def keywords() -> Generator[AuditdKeywords, None, None]:
    """Create keywords without global lab configuration or SSH access.

    Yields:
        AuditdKeywords: Keywords backed by a checked fake SSH channel.
    """
    with patch("keywords.base_keyword.get_logger"):
        kw = AuditdKeywords(NonCallableMagicMock(), "/etc/kubernetes/admin.conf")
        kw.ssh_connection.get_return_code.return_value = 0
        kw.k8s_config = K8sConfigExporter("/etc/kubernetes/admin.conf")
        kw.kubeconfig_path = "/etc/kubernetes/admin.conf"
        yield kw


@pytest.mark.parametrize("text", ["", "# comment\n", "broken", "=value", "key=", "key=one\nkey=two", "bad key=value"])
def test_invalid_config(text: str) -> None:
    """Reject empty and malformed configuration evidence.

    Args:
        text (str): Invalid configuration.
    """
    with pytest.raises(KeywordException):
        parse_audit_config(text)


def test_config_comments_and_embedded_equals() -> None:
    """Preserve values while ignoring blank and comment-only lines."""
    assert parse_audit_config("\n # heading\n log_file = /tmp/a=b#literal\n num_logs=5\n") == {"log_file": "/tmp/a=b#literal", "num_logs": "5"}


def test_poll_timeout_is_bounded() -> None:
    """Poll no more than the deadline and report missing evidence."""
    with patch("framework.validation.validation.time.time", side_effect=[0, 0, 5, 10]), patch("framework.validation.validation.sleep") as sleep:
        probe = MagicMock(return_value={})
        with pytest.raises(KeywordException, match="Timed out.*worker-0"):
            wait_for_audit(probe, "event on worker-0", timeout=10, interval=5)
        assert probe.call_count == 3
        assert sleep.call_count == 2


def test_poll_propagates_command_failure() -> None:
    """A failed query must not look like a successful empty observation."""
    probe = MagicMock(side_effect=KeywordException("SSH rc=1"))
    with pytest.raises(KeywordException, match="SSH rc=1"):
        wait_for_audit(probe, "event")
    probe.assert_called_once()


def test_poll_returns_evidence() -> None:
    """Return the observation so consumers can correlate its records."""
    with patch("framework.validation.validation.sleep"):
        assert wait_for_audit(MagicMock(side_effect=[{}, {"serial": 42}]), "event") == {"serial": 42}


@pytest.mark.parametrize("case", ["empty", "missing", "duplicate", "pending", "failed", "not_ready", "terminating", "missing_container", "waiting", "no_condition"])
def test_unhealthy_pods_cannot_pass(keywords: AuditdKeywords, case: str) -> None:
    """Reject incomplete or unhealthy pod coverage regardless of Running counts.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
        case (str): Evidence failure mode.
    """
    pods = [pod(host) for host in HOSTS]
    if case == "empty":
        pods = []
    elif case == "missing":
        pods.pop()
    elif case == "wrong_node":
        pods[-1]["spec"]["nodeName"] = "worker-9"
    elif case == "duplicate":
        pods.append(copy.deepcopy(pods[0]))
    elif case in ("pending", "failed"):
        pods[-1]["status"]["phase"] = case.title()
    elif case == "not_ready":
        pods[-1]["status"]["containerStatuses"][0]["ready"] = False
    elif case == "terminating":
        pods[-1]["metadata"]["deletionTimestamp"] = "now"
    elif case == "missing_container":
        pods[-1]["spec"]["containers"].append({"name": "sidecar"})
    elif case == "waiting":
        pods[-1]["status"]["containerStatuses"][0]["state"] = {"waiting": {"reason": "CrashLoopBackOff"}}
    elif case == "no_condition":
        pods[-1]["status"]["conditions"] = []
    keywords.ssh_connection.send.return_value = json.dumps({"items": pods})
    assert keywords.ready_pods(HOSTS) == {}
    assert "field-selector" not in keywords.ssh_connection.send.call_args.args[0]


def test_exact_ready_coverage(keywords: AuditdKeywords) -> None:
    """Return pod evidence keyed by the inventory nodes.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    keywords.ssh_connection.send.return_value = json.dumps({"items": [pod(host) for host in HOSTS]})
    assert set(keywords.wait_ready(HOSTS, timeout=0)) == set(HOSTS)


def test_empty_expected_hosts_rejected(keywords: AuditdKeywords) -> None:
    """Prevent vacuous coverage from an empty inventory.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    with pytest.raises(ValueError):
        keywords.ready_pods(())


def test_pod_command_failure(keywords: AuditdKeywords) -> None:
    """Do not parse stdout from a failed kubectl query.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    keywords.ssh_connection.send.return_value = '{"items": []}'
    keywords.ssh_connection.get_return_code.return_value = 1
    with patch("keywords.k8s.pods.kubectl_get_pods_keywords.get_logger"), patch("keywords.k8s.pods.kubectl_get_pods_keywords.time.sleep"), patch("keywords.k8s.pods.kubectl_get_pods_keywords.time.time", side_effect=[0, 0, 61]):
        with pytest.raises(KeywordException, match="Could not read the pod list"):
            keywords.discover_pods()


def test_wrong_node_exec_rejected(keywords: AuditdKeywords) -> None:
    """Never substitute a controller for a missing worker.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    with pytest.raises(ValueError, match="Unknown participating"):
        keywords.pod_command("worker-9", HOSTS, "auditctl -s")


def test_restart_requires_new_uid(keywords: AuditdKeywords) -> None:
    """A still-ready old pod does not satisfy replacement.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    ready = {host: pod(host) for host in HOSTS}
    with patch.object(keywords, "wait_ready", return_value=ready), patch.object(keywords, "ready_pods", return_value=ready), patch("keywords.cloud_platform.applications.auditd_keywords.KubectlDeletePodsKeywords"), patch.object(keywords, "verify_runtime") as verify:
        with pytest.raises(KeywordException, match="replacement audit pod"):
            keywords.restart_pod(HOSTS[0], HOSTS, timeout=0)
        verify.assert_not_called()


@pytest.mark.parametrize("status", ["", "enabled 0\npid 15", "enabled 1\npid 0", "enabled 2\npid 15"])
def test_bad_auditctl_status(keywords: AuditdKeywords, status: str) -> None:
    """Reject empty, disabled, absent and immutable daemon states.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
        status (str): Invalid auditctl output.
    """
    with patch.object(keywords, "wait_ready"), patch.object(keywords, "boot_audit", return_value="1"), patch.object(keywords, "pod_command", return_value=status):
        with pytest.raises(KeywordException, match="daemon"):
            keywords.verify_runtime(HOSTS)


def state_with_baseline(application: tuple[str, str] | None = ("1.0", "applied")) -> AuditdState:
    """Create a recoverable state with mock keyword collaborators.

    Args:
        application (tuple[str, str] | None): Original version/status.

    Returns:
        AuditdState: State with a populated baseline.
    """
    kw = MagicMock(spec=AuditdKeywords)
    kw.ssh_connection = NonCallableMagicMock()
    kw.application_state.return_value = application
    kw.kernel_parameter.return_value = "1"
    kw.boot_audit.return_value = "1"
    kw.participating_hosts.return_value = HOSTS
    kw.user_overrides.return_value = {"auditdconf": "original"}
    state = AuditdState(kw)
    state.baseline = AuditdBaseline(HOSTS, HOSTS[0], "1", application, {"auditdconf": "original"} if application else {}, {}, "/tmp/original.tgz")
    return state


def test_partial_prepare_registers_kernel_recovery() -> None:
    """A service-parameter failure still triggers original boot-state recovery."""
    state = state_with_baseline(("1.0", "uploaded"))
    state.baseline = AuditdBaseline(HOSTS, HOSTS[0], "0", ("1.0", "uploaded"), {}, {}, "/tmp/original.tgz")
    state.keywords.set_kernel_audit.side_effect = KeywordException("reboot failed")
    with pytest.raises(KeywordException, match="reboot failed"):
        state.prepare()
    assert state.kernel_touched
    state.keywords.set_kernel_audit.side_effect = None
    state.keywords.boot_audit.return_value = "0"
    state._restore_kernel()
    state.keywords.set_kernel_audit.assert_called_with("0", HOSTS)


def test_cleanup_continues_after_failure() -> None:
    """Report all cleanup errors while still attempting kernel and role recovery."""
    state = state_with_baseline()
    state.add_cleanup("consumer rules", MagicMock(side_effect=RuntimeError("rule failure")))
    with patch.object(state, "_restore_application", side_effect=RuntimeError("apply failure")), patch.object(state, "_restore_kernel") as kernel, patch.object(state, "_verify"):
        with pytest.raises(ExceptionGroup) as error:
            state.restore()
        assert len(error.value.exceptions) == 2
        kernel.assert_called_once()
        state.keywords.restore_controller.assert_called_once_with(HOSTS[0])
        assert not state.restored


def test_restore_uses_original_overrides() -> None:
    """Preserve user state instead of installing hardcoded defaults."""
    state = state_with_baseline()
    with patch.object(state, "set_overrides") as overrides:
        state._restore_application()
        overrides.assert_called_once_with({"auditdconf": "original"}, apply=True)
        state.keywords.delete.assert_not_called()
        state.keywords.upload.assert_not_called()


def test_restore_absent_baseline_removes_created_app() -> None:
    """Remove only the app created by the test when none existed initially."""
    state = state_with_baseline(None)
    state.keywords.application_state.side_effect = [("2.0", "applied"), None]
    state._restore_application()
    state.keywords.remove.assert_called_once()
    state.keywords.delete.assert_called_once()
    state.keywords.upload.assert_not_called()


def test_restore_original_version_after_update() -> None:
    """Restore from the original archive after a consumer changes versions."""
    state = state_with_baseline()
    state.keywords.application_state.side_effect = [("2.0", "applied"), ("1.0", "applied")]
    with patch.object(state, "validate_artifact") as validate, patch.object(state, "set_overrides"):
        state._restore_application()
        validate.assert_called_once_with("/tmp/original.tgz", "1.0")
        state.keywords.upload.assert_called_once_with("/tmp/original.tgz", "1.0")


def test_restore_uploaded_baseline_does_not_apply() -> None:
    """An uploaded original app remains uploaded after teardown."""
    state = state_with_baseline(("1.0", "uploaded"))
    state.keywords.application_state.side_effect = [("1.0", "applied"), ("1.0", "uploaded")]
    with patch.object(state, "set_overrides") as overrides:
        state._restore_application()
        state.keywords.remove.assert_called_once()
        overrides.assert_called_once_with({"auditdconf": "original"}, apply=False)


def test_pending_kernel_baseline_rejected() -> None:
    """Reject inconsistent boot/service state before any mutation."""
    state = state_with_baseline()
    state.baseline = None
    state.keywords.boot_audit.return_value = "0"
    with pytest.raises(KeywordException, match="Pending/inconsistent"):
        state.capture("/tmp/original.tgz")
    state.keywords.set_kernel_audit.assert_not_called()


def test_existing_app_requires_recovery_artifact() -> None:
    """Missing original content is a precondition error before installation."""
    state = state_with_baseline()
    state.baseline = None
    with pytest.raises(KeywordException, match="original-version"):
        state.capture()
    state.keywords.apply.assert_not_called()


def test_setup_registers_finalizer_before_setup_failure() -> None:
    """The explicit setup helper registers recovery before preparation can fail."""
    from keywords.cloud_platform.applications.auditd_state import setup_auditd

    request = MagicMock()
    request.param = {"prepare": True}
    state = MagicMock()
    state.prepare.side_effect = RuntimeError("setup failed")
    with patch("keywords.cloud_platform.applications.auditd_state.ConfigurationManager") as configuration, patch("keywords.cloud_platform.applications.auditd_state.AuditdState", return_value=state), patch("keywords.cloud_platform.applications.auditd_state.AuditdKeywords"), patch("keywords.cloud_platform.applications.auditd_state.LabConnectionKeywords"):
        configuration.get_app_config.return_value.get_auditd_test_options.return_value = {}
        with pytest.raises(RuntimeError, match="setup failed"):
            setup_auditd(request, prepare=True)
        request.addfinalizer.assert_called_once_with(state.restore)
        state.capture.assert_called_once()


def test_restore_upload_failure_deletes_partial_record() -> None:
    """A failed upload can be deleted without attempting removal of workloads."""
    state = state_with_baseline(None)
    state.keywords.application_state.side_effect = [("2.0", "upload-failed"), None]
    state._restore_application()
    state.keywords.delete.assert_called_once()
    state.keywords.remove.assert_not_called()


def test_kernel_recovery_precedes_applied_app() -> None:
    """An enabled baseline must boot correctly before reapplying its workload."""
    state = state_with_baseline()
    order = []
    with patch.object(state, "_restore_kernel", side_effect=lambda: order.append("kernel")), patch.object(state, "_restore_application", side_effect=lambda: order.append("application")), patch.object(state, "_verify"):
        state.restore()
    assert order == ["kernel", "application"]


def test_recovery_is_idempotent_after_success() -> None:
    """A completed finalizer does not perform the same lab operations twice."""
    state = state_with_baseline()
    with patch.object(state, "_restore_kernel"), patch.object(state, "_restore_application") as application, patch.object(state, "_verify"):
        state.restore()
        state.restore()
        application.assert_called_once()


def test_rule_order_preserved(keywords: AuditdKeywords) -> None:
    """Reinstall rules in their original order since audit matching is ordered.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    import shlex

    original = ["-a never,exit -F dir=/tmp/excluded", "-a always,exit -F dir=/tmp"]
    with patch.object(keywords, "wait_ready", return_value={host: pod(host) for host in HOSTS}), patch.object(keywords, "pod_command", return_value="No rules") as command:
        keywords.restore_rules((HOSTS[0],), {HOSTS[0]: {"rules": original}})
        shell_call = command.call_args_list[1].args[2]
        script = shlex.split(shell_call)[2]
        assert script.index(original[0]) < script.index(original[1])
        assert "auditctl -R" in command.call_args_list[2].args[2]
        assert "rm -f" in command.call_args_list[3].args[2]


def test_rule_restore_continues_other_hosts(keywords: AuditdKeywords) -> None:
    """One unreachable node does not prevent another node's recovery attempt.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    with patch.object(keywords, "wait_ready", return_value={host: pod(host) for host in HOSTS}), patch.object(keywords, "pod_command", side_effect=[KeywordException("lost node"), "No rules"]) as command:
        with pytest.raises(ExceptionGroup, match="rule restoration"):
            keywords.restore_rules(HOSTS, {host: {"rules": ["No rules"]} for host in HOSTS})
        assert [call.args[0] for call in command.call_args_list] == list(HOSTS)


def test_interrupted_apply_is_aborted(keywords: AuditdKeywords) -> None:
    """Wait for a terminal state after aborting a timed-out apply.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    with patch.object(keywords, "application_state", side_effect=[("1", "applying"), ("1", "apply-failed")]), patch("keywords.cloud_platform.applications.auditd_keywords.SystemApplicationAbortKeywords") as abort, patch("keywords.cloud_platform.applications.auditd_keywords.SystemApplicationListKeywords") as applications:
        keywords.settle_application()
        abort.return_value.system_application_abort.assert_called_once_with("auditd")
        applications.return_value.validate_app_status_in_list.assert_called_once_with("auditd", ["uploaded", "applied", "upload-failed", "apply-failed", "remove-failed", "update-failed"], timeout=300, polling_sleep_time=5)


def test_kernel_enable_checks_every_node(keywords: AuditdKeywords) -> None:
    """Use supported service and reboot APIs, then recheck each changed host.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    with patch.object(keywords, "kernel_parameter", return_value="0"), patch.object(keywords, "boot_audit", side_effect=["0", "1", "0", "1"]) as boot, patch(f"{module}.SystemServiceParameterKeywords") as service, patch(f"{module}.SystemHostLockKeywords") as locks, patch(f"{module}.SystemHostSwactKeywords") as swact:
        locks.return_value.ensure_host_unlocked.return_value = False
        keywords.set_kernel_audit("1", HOSTS)
        service.return_value.modify_service_parameter.assert_called_once_with("platform", "kernel", "audit", "1")
        service.return_value.apply_service_parameters.assert_called_once_with("platform")
        assert [call.args[0] for call in boot.call_args_list] == [HOSTS[0], HOSTS[0], HOSTS[1], HOSTS[1]]
        assert [call.args[0] for call in locks.return_value.ensure_host_unlocked.call_args_list] == list(HOSTS)
        assert locks.return_value.unlock_host.call_count == 2
        assert swact.return_value.swact_if_active.call_count == 2


def test_empty_override_restore_deletes_user_values() -> None:
    """Restore a truly empty baseline without retaining test override keys."""
    state = state_with_baseline()
    state.keywords.user_overrides.side_effect = [{"test": "value"}, {}]
    with patch("keywords.cloud_platform.applications.auditd_state.SystemHelmOverrideKeywords") as helm:
        state.set_overrides({}, apply=False)
        helm.return_value.delete_system_helm_override.assert_called_once_with("auditd", "auditd", "kube-system")
        state.keywords.apply.assert_not_called()


def test_override_failure_cleans_only_owned_file() -> None:
    """Delete the exact generated YAML path even when helm update fails."""
    state = state_with_baseline()
    with patch("keywords.cloud_platform.applications.auditd_state.SystemHelmOverrideKeywords") as helm:
        helm.return_value.update_helm_override.side_effect = KeywordException("helm failed")
        with pytest.raises(KeywordException, match="helm failed"):
            state.set_overrides({"auditdconf": "log_file=/var/log/audit/test.log"})
    commands = [call.args[0] for call in state.keywords.command.call_args_list]
    path = commands[0].split("> ")[1]
    assert commands[-1] == f"rm -f -- {path}"
    assert path.startswith("/tmp/auditd-test-")


def test_app_config_defaults_and_optional_audit_options(tmp_path: Path) -> None:
    """Existing app configuration remains valid without audit-specific settings.

    Args:
        tmp_path (Path): Pytest temporary directory.
    """
    from config.app.objects.app_config import AppConfig

    path = tmp_path / "apps.json"
    content = {"base_application_path": "/tmp", "platform_integ_app_tarball": "unused", "metrics_server_app_tarball": "unused"}
    path.write_text(json.dumps(content))
    assert AppConfig(str(path)).get_auditd_test_options() == {}
    content["auditd_test_options"] = {"baseline_artifact": "/tmp/baseline.tgz"}
    path.write_text(json.dumps(content))
    config = AppConfig(str(path))
    options = config.get_auditd_test_options()
    options.clear()
    assert config.get_auditd_test_options() == content["auditd_test_options"]


@pytest.mark.parametrize("text", ["audit=10", "audit=0 audit=1", "no_audit=1", "audit=1extra", ""])
def test_exact_kernel_argument(keywords: AuditdKeywords, text: str) -> None:
    """Substring matches cannot falsely prove kernel enablement.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
        text (str): Invalid boot command line.
    """
    with patch.object(keywords, "node_command", return_value=text):
        with pytest.raises(KeywordException, match="boot argument"):
            keywords.boot_audit(HOSTS[0])


def test_capture_absent_baseline() -> None:
    """An absent baseline needs no recovery archive and records the host set."""
    state = state_with_baseline(None)
    state.baseline = None
    state.keywords.discover_pods.return_value = []
    state.keywords.active_controller.return_value = HOSTS[0]
    baseline = state.capture()
    assert baseline.application is None
    assert baseline.hosts == HOSTS
    assert baseline.kernel == "1"
    assert baseline.controller == HOSTS[0]
    state.keywords.apply.assert_not_called()


def test_capture_applied_baseline_preserves_effective_rules() -> None:
    """Snapshot the original settings and ordered rules before setup changes."""
    state = state_with_baseline()
    state.baseline = None
    effective = {host: {"config": {"log_file": "/var/log/audit/audit.log"}, "rules": ["No rules"]} for host in HOSTS}
    state.keywords.effective_settings.return_value = effective
    state.keywords.combined_config.return_value = {"log_file": "/var/log/audit/audit.log"}
    with patch.object(state, "validate_artifact"):
        baseline = state.capture("/tmp/original.tgz")
    assert baseline.effective == effective
    assert baseline.overrides == {"auditdconf": "original"}
    state.keywords.verify_runtime.assert_called_once_with(HOSTS)


def test_missing_metadata_rejected_before_mutation() -> None:
    """Do not accept an archive just because its filename looks correct."""
    state = state_with_baseline()
    state.keywords.command.return_value = "charts/auditd.tgz\n"
    with pytest.raises(KeywordException, match="metadata.yaml"):
        state.validate_artifact("/tmp/original.tgz", "1.0")
    state.keywords.upload.assert_not_called()


def test_wrong_artifact_version_rejected() -> None:
    """Metadata must identify the exact recovery version."""
    state = state_with_baseline()
    state.keywords.command.side_effect = ["metadata.yaml", "app_name: auditd\napp_version: wrong"]
    with pytest.raises(KeywordException, match="must contain auditd version"):
        state.validate_artifact("/tmp/original.tgz", "1.0")


def test_artifact_must_match_on_both_controllers() -> None:
    """Swact recovery cannot rely on different content at the same path."""
    state = state_with_baseline()
    state.keywords.command.side_effect = ["metadata.yaml", "app_name: auditd\napp_version: '1.0'"]
    state.keywords.node_command.side_effect = [f"{'a' * 64} /tmp/original.tgz", f"{'b' * 64} /tmp/original.tgz"]
    with patch("keywords.cloud_platform.applications.auditd_state.SystemHostListKeywords") as hosts:
        hosts.return_value.get_controllers.return_value = [MagicMock(), MagicMock()]
        with pytest.raises(KeywordException, match="same audit recovery artifact"):
            state.validate_artifact("/tmp/original.tgz", "1.0")


def test_node_connection_identity_checked(keywords: AuditdKeywords) -> None:
    """A wrong SSH mapping must not validate the same machine as two nodes.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    connection = managed_connection()
    connection.send.return_value = "controller-0\n"
    connection.get_return_code.return_value = 0
    with patch(f"{module}.SystemHostListKeywords") as inventory, patch(f"{module}.LabConnectionKeywords") as connections:
        inventory.return_value.get_controllers.return_value = []
        connections.return_value.get_compute_ssh.return_value = connection
        with pytest.raises(KeywordException, match="Expected SSH node worker-0"):
            keywords.node_command("worker-0", "cat /proc/cmdline")
        connection.send.assert_called_once_with("hostname")
        connection.close.assert_called_once()


def test_kernel_failure_does_not_skip_other_nodes(keywords: AuditdKeywords) -> None:
    """A failed controller reboot still permits independent worker recovery.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    with patch.object(keywords, "kernel_parameter", return_value="0"), patch.object(keywords, "boot_audit", side_effect=[KeywordException("node unavailable"), "0", "1"]) as boot, patch(f"{module}.SystemServiceParameterKeywords"), patch(f"{module}.SystemHostLockKeywords") as locks, patch(f"{module}.SystemHostSwactKeywords"):
        locks.return_value.ensure_host_unlocked.return_value = False
        with pytest.raises(ExceptionGroup, match="every host"):
            keywords.set_kernel_audit("1", HOSTS)
        assert boot.call_count == 3
        locks.return_value.unlock_host.assert_called_once_with("worker-0")


@pytest.mark.parametrize("operation,exec_count", [("verify_runtime", 4), ("effective_settings", 8), ("restore_rules", 16)])
def test_one_pod_discovery_per_operation(keywords: AuditdKeywords, operation: str, exec_count: int) -> None:
    """Multi-host operations reuse a snapshot while preserving checked executions.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
        operation (str): Operation measured with four hosts.
        exec_count (int): Required container commands for that operation.
    """
    hosts = ("controller-0", "controller-1", "worker-0", "worker-1")
    records = [pod(host) for host in hosts]

    def respond(command: str) -> str:
        if "get pods" in command:
            return json.dumps({"items": records})
        if "auditctl -s" in command:
            return "enabled 1\npid 123"
        if "auditctl -l" in command:
            return "No rules"
        if "cat /etc/audit/auditd.conf" in command:
            return "log_file = /var/log/audit/audit.log"
        return ""

    keywords.ssh_connection.send.side_effect = respond
    with patch.object(keywords, "boot_audit", return_value="1"):
        if operation == "restore_rules":
            keywords.restore_rules(hosts, {host: {"rules": ["-w /tmp/example -p wa"]} for host in hosts})
        else:
            getattr(keywords, operation)(hosts)
    commands = [call.args[0] for call in keywords.ssh_connection.send.call_args_list]
    assert sum("get pods" in command for command in commands) == 1
    assert sum("kubectl exec" in command for command in commands) == exec_count


def test_unexpected_assigned_node_fails_without_poll_delay(keywords: AuditdKeywords) -> None:
    """Do not wait through the timeout for an inventory mismatch.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    keywords.ssh_connection.send.return_value = json.dumps({"items": [pod("worker-9")]})
    with patch("framework.validation.validation.sleep") as sleep:
        with pytest.raises(KeywordException, match="unexpected node worker-9"):
            keywords.wait_ready(HOSTS)
        sleep.assert_not_called()
    keywords.ssh_connection.send.assert_called_once()


def test_duplicate_rollout_pods_converge(keywords: AuditdKeywords) -> None:
    """A temporary duplicate must not fail a legitimate replacement rollout.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    records = [pod(host) for host in HOSTS]
    keywords.ssh_connection.send.side_effect = [json.dumps({"items": records + [pod(HOSTS[0], "replacement")]}), json.dumps({"items": records})]
    with patch("framework.validation.validation.sleep"), patch("keywords.cloud_platform.applications.auditd_keywords.get_logger") as logger:
        assert set(keywords.wait_ready(HOSTS)) == set(HOSTS)
        assert any("duplicate pod" in call.args[0] for call in logger.return_value.log_info.call_args_list)


def test_readiness_timeout_preserves_last_observation(keywords: AuditdKeywords) -> None:
    """Report missing hosts without querying again after the timeout.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    keywords.ssh_connection.send.return_value = '{"items": []}'
    with pytest.raises(KeywordException, match="last readiness observation: missing audit pods"):
        keywords.wait_ready(HOSTS, timeout=0)
    keywords.ssh_connection.send.assert_called_once()


def test_snapshot_does_not_survive_an_operation(keywords: AuditdKeywords) -> None:
    """A later operation executes against the replacement pod identity.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    first = {host: pod(host) for host in HOSTS}
    second = copy.deepcopy(first)
    second[HOSTS[0]]["metadata"].update(name="auditd-replacement", uid="new")
    with patch.object(keywords, "wait_ready", side_effect=[first, second]) as discover, patch("keywords.cloud_platform.applications.auditd_keywords.KubectlExecInPodsKeywords") as execution:
        execution.return_value.run_pod_exec_cmd.return_value = "ok"
        keywords.pod_command(HOSTS[0], HOSTS, "auditctl -s")
        keywords.pod_command(HOSTS[0], HOSTS, "auditctl -s")
        assert discover.call_count == 2
        assert [call.args[0] for call in execution.return_value.run_pod_exec_cmd.call_args_list] == [first[HOSTS[0]]["metadata"]["name"], "auditd-replacement"]


def test_snapshot_rejects_swapped_node_mapping(keywords: AuditdKeywords) -> None:
    """A caller cannot map a healthy worker pod to a controller by mistake.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    swapped = {HOSTS[0]: pod(HOSTS[1]), HOSTS[1]: pod(HOSTS[0])}
    with pytest.raises(KeywordException, match="Invalid audit pod snapshot"):
        keywords.pod_command(HOSTS[0], HOSTS, "auditctl -s", pods=swapped)
    keywords.ssh_connection.send.assert_not_called()


def test_node_session_reuses_and_releases_connections(keywords: AuditdKeywords) -> None:
    """Nested read operations share a handshake, then the next operation reconnects.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    connection = managed_connection()
    connection.send.side_effect = lambda command: "worker-0" if command == "hostname" else "audit=1"
    connection.get_return_code.return_value = 0
    with patch(f"{module}.SystemHostListKeywords") as inventory, patch(f"{module}.LabConnectionKeywords") as lab:
        inventory.return_value.get_controllers.return_value = []
        lab.return_value.get_compute_ssh.side_effect = lambda hostname: register_connection(connection)
        with keywords.node_session():
            keywords.node_command("worker-0", "cat /proc/cmdline")
            with keywords.node_session():
                keywords.node_command("worker-0", "cat /proc/cmdline")
            connection.close.assert_not_called()
            assert inventory.return_value.get_controllers.call_count == 1
        connection.close.assert_called_once()
        keywords.node_command("worker-0", "cat /proc/cmdline")
        assert lab.return_value.get_compute_ssh.call_count == 2
        assert connection.close.call_count == 2
        assert keywords._node_connections is None


def test_failed_node_command_discards_session(keywords: AuditdKeywords) -> None:
    """A failed command cannot leave a bad connection cached for the next probe.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    failed, replacement = managed_connection(), managed_connection()
    failed.send.side_effect = ["worker-0", "failure"]
    failed.get_return_code.side_effect = [0, 1]
    replacement.send.side_effect = ["worker-0", "audit=1"]
    replacement.get_return_code.return_value = 0
    with patch(f"{module}.SystemHostListKeywords") as inventory, patch(f"{module}.LabConnectionKeywords") as lab:
        inventory.return_value.get_controllers.return_value = []
        lab.return_value.get_compute_ssh.side_effect = [failed, replacement]
        with keywords.node_session():
            with pytest.raises(KeywordException, match="Audit command failed"):
                keywords.node_command("worker-0", "cat /proc/cmdline")
            assert keywords.node_command("worker-0", "cat /proc/cmdline") == "audit=1"
        failed.close.assert_called_once()
        replacement.close.assert_called_once()


def test_invalidation_reconnects_before_next_node_command(keywords: AuditdKeywords) -> None:
    """Disruptive operations cannot reuse a pre-action connection.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    connection = managed_connection()
    connection.send.return_value = "worker-0"
    connection.get_return_code.return_value = 0
    with patch(f"{module}.SystemHostListKeywords") as inventory, patch(f"{module}.LabConnectionKeywords") as lab:
        inventory.return_value.get_controllers.return_value = []
        lab.return_value.get_compute_ssh.side_effect = lambda hostname: register_connection(connection)
        with keywords.node_session():
            keywords.node_command("worker-0", "hostname")
            keywords.invalidate_node_sessions()
            connection.close.assert_called_once()
            keywords.node_command("worker-0", "hostname")
        assert lab.return_value.get_compute_ssh.call_count == 2
        assert connection.close.call_count == 2


def test_managed_node_session_is_removed_on_exit(keywords: AuditdKeywords) -> None:
    """Closing an operation also removes the framework manager's bookkeeping.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    connection = managed_connection()
    connection.get_name.return_value = "worker-0"
    with patch(f"{module}.SSHConnectionManager") as manager:
        manager.get_ssh_connection.return_value = connection
        with keywords.node_session():
            keywords._node_connections["worker-0"] = connection
        manager.remove_ssh_connection.assert_called_once_with("worker-0")
        connection.close.assert_not_called()


@pytest.mark.parametrize("source", ["configuration", "parameters"])
def test_setup_unknown_option_identifies_source(source: str) -> None:
    """Reject misspelled options before opening a lab connection.

    Args:
        source (str): Location of the invalid option.
    """
    from keywords.cloud_platform.applications.auditd_state import setup_auditd

    request = MagicMock()
    request.param = {"typo": True} if source == "parameters" else {}
    options = {"typo": True} if source == "configuration" else {}
    with patch("keywords.cloud_platform.applications.auditd_state.ConfigurationManager") as configuration, patch("keywords.cloud_platform.applications.auditd_state.LabConnectionKeywords") as lab:
        configuration.get_app_config.return_value.get_auditd_test_options.return_value = options
        expected = "app configuration auditd_test_options" if source == "configuration" else "audit setup options"
        with pytest.raises(ValueError, match=f"Unknown keys in {expected}:.*typo"):
            setup_auditd(request, options=request.param)
        lab.assert_not_called()


def test_recovery_logs_stage_failure_and_continues() -> None:
    """A failed recovery stage is visible even while later stages are attempted."""
    state = state_with_baseline()
    with patch.object(state, "_restore_application", side_effect=RuntimeError("apply failed")), patch.object(state, "_restore_kernel"), patch.object(state, "_verify"), patch("keywords.cloud_platform.applications.auditd_state.get_logger") as logger:
        with pytest.raises(ExceptionGroup):
            state.restore()
        assert any("application: apply failed" in call.args[0] for call in logger.return_value.log_warning.call_args_list)
        assert any("completed: verification" in call.args[0] for call in logger.return_value.log_info.call_args_list)


def test_constructor_defines_session_state(keywords: AuditdKeywords) -> None:
    """Cleanup and invalidation are safe before the first node command.

    Args:
        keywords (AuditdKeywords): Constructed keywords with fake controller SSH.
    """
    assert keywords._node_connections is None
    assert keywords._node_controllers is None
    keywords.invalidate_node_sessions()
    with keywords.node_session():
        assert keywords._node_connections == {}
    assert keywords._node_connections is None


def test_node_identity_checked_once_per_connection(keywords: AuditdKeywords) -> None:
    """Cached commands avoid redundant hostname checks but still validate status.

    Args:
        keywords (AuditdKeywords): Constructed keywords with fake controller SSH.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    connection = managed_connection()
    connection.send.side_effect = ["worker-0", "first result", "second result"]
    connection.get_return_code.return_value = 0
    # The controller's previous status must not be used for a node command.
    keywords.ssh_connection.get_return_code.return_value = 1
    with patch(f"{module}.SystemHostListKeywords") as inventory, patch(f"{module}.LabConnectionKeywords") as lab, patch.object(keywords, "validate_success_return_code", wraps=keywords.validate_success_return_code) as validate:
        inventory.return_value.get_controllers.return_value = []
        lab.return_value.get_compute_ssh.return_value = connection
        with keywords.node_session():
            assert keywords.node_command("worker-0", "first") == "first result"
            assert keywords.node_command("worker-0", "second") == "second result"
        assert [call.args[0] for call in connection.send.call_args_list] == ["hostname", "first", "second"]
        assert validate.call_count == 3
        assert all(call.args[0] is connection for call in validate.call_args_list)


def test_rejected_hostname_command_is_not_cached(keywords: AuditdKeywords) -> None:
    """An identity query with nonzero status cannot establish a usable session.

    Args:
        keywords (AuditdKeywords): Constructed keywords with fake controller SSH.
    """
    module = "keywords.cloud_platform.applications.auditd_keywords"
    connection = managed_connection()
    connection.send.return_value = "worker-0"
    connection.get_return_code.return_value = 1
    with patch(f"{module}.SystemHostListKeywords") as inventory, patch(f"{module}.LabConnectionKeywords") as lab:
        inventory.return_value.get_controllers.return_value = []
        lab.return_value.get_compute_ssh.return_value = connection
        with pytest.raises(AssertionError, match="Return code was 1"):
            keywords.node_command("worker-0", "must not execute")
        connection.send.assert_called_once_with("hostname")
        assert SSHConnectionManager.get_ssh_connection(connection.get_name()) is None
        connection.close.assert_called_once()


def test_controller_command_uses_framework_validator(keywords: AuditdKeywords) -> None:
    """Controller command errors retain context after the standard status check.

    Args:
        keywords (AuditdKeywords): Constructed keywords with fake controller SSH.
    """
    keywords.ssh_connection.send.return_value = "permission denied"
    keywords.ssh_connection.get_return_code.return_value = 1
    with patch.object(keywords, "validate_success_return_code", wraps=keywords.validate_success_return_code) as validate:
        with pytest.raises(KeywordException, match="permission denied"):
            keywords.command("example")
        validate.assert_called_once_with(keywords.ssh_connection)


def test_cleanup_does_not_close_another_managed_connection(keywords: AuditdKeywords) -> None:
    """An ownership mismatch must not close another caller's manager entry.

    Args:
        keywords (AuditdKeywords): Constructed keywords with fake controller SSH.
    """
    original = managed_connection()
    replacement = managed_connection()
    SSHConnectionManager.ssh_connection_list[original.get_name()] = replacement
    with pytest.raises(KeywordException, match="belongs to another connection"):
        keywords._close_node_connection(original)
    original.close.assert_not_called()
    replacement.close.assert_not_called()


def test_cleanup_already_released_connection_is_noop(keywords: AuditdKeywords) -> None:
    """Cleanup does not directly close a connection removed by the framework.

    Args:
        keywords (AuditdKeywords): Constructed keywords with fake controller SSH.
    """
    connection = managed_connection()
    SSHConnectionManager.remove_ssh_connection(connection.get_name())
    keywords._close_node_connection(connection)
    connection.close.assert_called_once()


def test_explicit_setup_does_not_prepare_by_default() -> None:
    """Lifecycle consumers can capture state and drive installation themselves."""
    from keywords.cloud_platform.applications.auditd_state import setup_auditd

    module = "keywords.cloud_platform.applications.auditd_state"
    request, state = MagicMock(), MagicMock()
    with patch(f"{module}.ConfigurationManager") as config, patch(f"{module}.LabConnectionKeywords"), patch(f"{module}.AuditdKeywords"), patch(f"{module}.AuditdState", return_value=state):
        config.get_app_config.return_value.get_auditd_test_options.return_value = {}
        assert setup_auditd(request) is state
        request.addfinalizer.assert_called_once_with(state.restore)
        state.capture.assert_called_once_with(None)
        state.prepare.assert_not_called()


def test_setup_preparation_is_explicit_and_preserves_config() -> None:
    """Per-call artifact data overrides config after recovery is registered."""
    from keywords.cloud_platform.applications.auditd_state import setup_auditd

    module = "keywords.cloud_platform.applications.auditd_state"
    request, state = MagicMock(), MagicMock()
    options = {"baseline_artifact": "/original.tgz", "artifact": "/old.tgz", "version": "1"}
    steps = []
    request.addfinalizer.side_effect = lambda callback: steps.append("registered")
    state.prepare.side_effect = lambda *args: steps.append("prepared")
    with patch(f"{module}.ConfigurationManager") as config, patch(f"{module}.LabConnectionKeywords"), patch(f"{module}.AuditdKeywords"), patch(f"{module}.AuditdState", return_value=state):
        config.get_app_config.return_value.get_auditd_test_options.return_value = options
        setup_auditd(request, prepare=True, options={"artifact": "/new.tgz", "version": "2"})
        state.capture.assert_called_once_with("/original.tgz")
        state.prepare.assert_called_once_with("/new.tgz", "2")
        assert steps == ["registered", "prepared"]
        assert options["artifact"] == "/old.tgz"


def test_oidc_and_audit_options_are_independent(tmp_path: Path) -> None:
    """Keep the existing OIDC sample-app selector separate from audit setup.

    Args:
        tmp_path (Path): Pytest temporary directory.
    """
    from config.app.objects.app_config import AppConfig

    path = tmp_path / "apps.json"
    path.write_text(json.dumps({"base_application_path": "/tmp", "platform_integ_app_tarball": "unused", "metrics_server_app_tarball": "unused", "oidc_test_app_tarball": "different-oidc-test-app", "auditd_test_options": {"artifact": "/audit.tgz", "version": "1"}}))
    config = AppConfig(str(path))
    assert config.get_oidc_test_app_tarball() == "different-oidc-test-app"
    assert config.get_auditd_test_options() == {"artifact": "/audit.tgz", "version": "1"}


def test_absent_app_skips_shared_status_wait(keywords: AuditdKeywords) -> None:
    """Do not query status for a confirmed absent application.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    with patch.object(keywords, "application_state", return_value=None), patch("keywords.cloud_platform.applications.auditd_keywords.SystemApplicationListKeywords") as applications:
        keywords.settle_application()
        applications.assert_not_called()


def test_interrupted_lock_uses_shared_recovery(keywords: AuditdKeywords) -> None:
    """Recover a locked host before deciding whether to reboot again.

    Args:
        keywords (AuditdKeywords): Fake SSH keywords.
    """
    from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords

    module = "keywords.cloud_platform.applications.auditd_keywords"
    locks = SystemHostLockKeywords(keywords.ssh_connection)
    with patch.object(keywords, "kernel_parameter", return_value="1"), patch.object(keywords, "boot_audit", return_value="1"), patch(f"{module}.SystemServiceParameterKeywords"), patch(f"{module}.SystemHostLockKeywords", return_value=locks), patch.object(locks, "is_host_locked", return_value=True), patch.object(locks, "unlock_host") as unlock, patch.object(locks, "lock_host") as lock:
        keywords.set_kernel_audit("1", (HOSTS[0],))
        unlock.assert_called_once_with(HOSTS[0], unlock_accepted_timeout=300, exclude_alarm_ids=None)
        lock.assert_not_called()


@pytest.mark.parametrize(
    "status,output,accepted",
    [
        (1, "<no matches>\ncommand terminated with exit code 1\n", True),
        (1, "permission denied\n<no matches>\ncommand terminated with exit code 1\n", False),
        (1, "command terminated with exit code 1\n", False),
        (2, "<no matches>\ncommand terminated with exit code 2\n", False),
        (0, "<no matches>\ncommand terminated with exit code 1\n", False),
    ],
)
def test_search_validates_real_pod_exec_output_and_status(keywords: AuditdKeywords, status: int, output: str, accepted: bool) -> None:
    """Let the output parser distinguish no matches from exec failures.

    Args:
        keywords (AuditdKeywords): Keywords backed by the fake SSH channel.
        status (int): Kubectl exec return code.
        output (str): Combined container and kubectl output.
        accepted (bool): Whether the output describes a valid empty result.
    """
    keywords.ssh_connection.send.return_value = output
    keywords.ssh_connection.get_return_code.return_value = status
    with patch.object(keywords, "wait_ready", return_value={host: pod(host) for host in HOSTS}):
        if accepted:
            assert keywords.search_syscall_events(HOSTS[0], HOSTS, "fresh", "rmdir").events == {}
        else:
            with pytest.raises(KeywordException):
                keywords.search_syscall_events(HOSTS[0], HOSTS, "fresh", "rmdir")
    command = keywords.ssh_connection.send.call_args.args[0]
    assert "-- env LC_ALL=C ausearch --input-logs --interpret -k fresh -sc rmdir" in command
    assert "case " not in command


def test_pod_commands_still_reject_nonzero_status_by_default(keywords: AuditdKeywords) -> None:
    """Only explicit output-parser callers may inspect a failed command themselves.

    Args:
        keywords (AuditdKeywords): Keywords backed by the fake SSH channel.
    """
    keywords.ssh_connection.send.return_value = "permission denied"
    keywords.ssh_connection.get_return_code.return_value = 1
    with patch.object(keywords, "wait_ready", return_value={host: pod(host) for host in HOSTS}):
        with pytest.raises(AssertionError):
            keywords.pod_command(HOSTS[0], HOSTS, "auditctl -s")
