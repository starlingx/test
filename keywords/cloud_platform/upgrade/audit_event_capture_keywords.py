"""Fresh audit-event validation across platform release changes."""

from shlex import quote
from uuid import uuid4

from pytest import FixtureRequest

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.applications.auditd_keywords import AuditdKeywords, wait_for_audit


class AuditEventCaptureKeywords(BaseKeyword):
    """Prove the node's audit daemon records a newly generated host syscall."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        super().__init__()
        self.audit = AuditdKeywords(ssh_connection)

    def validate_event_capture(self, request: FixtureRequest, phase: str, hosts: tuple[str, ...]) -> None:
        """Generate and correlate a fresh rmdir event on every participating node.

        Leave the existing application, Helm values and rules intact. Each action
        has its own temporary rule key and host path. Remove those artifacts
        before the next deploy step, and retain a finalizer for partial failures.

        Args:
            request (FixtureRequest): Pytest request for failure-path cleanup.
            phase (str): Phase name used in diagnostic evidence.
            hosts (tuple[str, ...]): Original controller and worker inventory.
        """
        if not hosts or len(set(hosts)) != len(hosts):
            raise ValueError("Audit event capture requires a nonempty, unique host inventory")
        self.audit.verify_runtime(hosts)
        for hostname in hosts:
            self._validate_node(request, phase, hosts, hostname)

    def _validate_node(self, request: FixtureRequest, phase: str, hosts: tuple[str, ...], hostname: str) -> None:
        """Check one node with cleanup registered before the first mutation.

        Args:
            request (FixtureRequest): Pytest cleanup owner.
            phase (str): Phase for diagnostics.
            hosts (tuple[str, ...]): Complete expected inventory.
            hostname (str): Node on which the action and audit read must run.
        """
        token = uuid4().hex[:20]
        key = f"stxtest_{token}"
        path = f"/tmp/stxtest-audit-{token}"
        rule = f"always,exit -F arch=b64 -S rmdir -k {quote(key)}"
        directory_created = False
        rule_attempted = False
        cleaned = False

        def cleanup():
            nonlocal cleaned, directory_created, rule_attempted
            if cleaned:
                return
            errors = []
            # Remove only this rule. A blanket auditctl -D would destroy user rules.
            if rule_attempted:
                try:
                    rules = self.audit.pod_command(hostname, hosts, "auditctl -l")
                    if key in rules:
                        self.audit.pod_command(hostname, hosts, f"auditctl -d {rule}")
                    if key in self.audit.pod_command(hostname, hosts, "auditctl -l"):
                        raise KeywordException(f"Temporary audit rule still present on {hostname}: {key}")
                    rule_attempted = False
                except Exception as error:
                    errors.append(KeywordException(f"[{phase}] rule cleanup on {hostname}, key={key}: {error}"))
            if directory_created:
                try:
                    # rmdir tolerates an already removed directory, but never deletes contents.
                    self.audit.node_command(hostname, f"sh -c {quote(f'if test -d {quote(path)}; then rmdir -- {quote(path)}; fi')}")
                    directory_created = False
                except Exception as error:
                    errors.append(KeywordException(f"[{phase}] path cleanup on {hostname}, path={path}: {error}"))
            if errors:
                raise ExceptionGroup("Audit event artifact cleanup failed", errors)
            cleaned = True

        request.addfinalizer(cleanup)
        directory_created = True
        self.audit.node_command(hostname, f"mkdir -- {quote(path)}")
        # Mark before sending: a command can install the rule before its response fails.
        rule_attempted = True
        # Prepend so an existing broader syscall rule cannot consume the event first.
        self.audit.pod_command(hostname, hosts, f"auditctl -A {rule}")
        self.audit.node_command(hostname, f"rmdir -- {quote(path)}")
        event_id = wait_for_audit(
            lambda: self.audit.search_syscall_events(hostname, hosts, key, "rmdir").successful_rmdir_event(key, path),
            f"[{phase}] audit rmdir key={key} path={path} on {hostname}",
        )
        get_logger().log_info(f"[{phase}] audit event on {hostname}: id={event_id} key={key} path={path}")
        cleanup()
