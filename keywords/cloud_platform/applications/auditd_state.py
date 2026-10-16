"""Recoverable audit test baseline shared by installation and regression tests."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath
from shlex import quote
from uuid import uuid4

import yaml
from pytest import FixtureRequest

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.applications.auditd_keywords import AuditdKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


@dataclass(frozen=True)
class AuditdBaseline:
    """Captured platform state; no assumptions about default user overrides."""

    hosts: tuple[str, ...]
    controller: str
    kernel: str
    application: tuple[str, str] | None
    overrides: dict
    effective: dict
    artifact: str | None


class AuditdState:
    """Capture before mutation and restore independently of setup success.

    Consumers register their extra recovery actions before changing runtime rules
    or creating host paths. Actions execute in reverse order before app recovery;
    every independent recovery stage is attempted and failures are aggregated.
    """

    def __init__(self, keywords: AuditdKeywords) -> None:
        self.keywords = keywords
        self.baseline: AuditdBaseline | None = None
        self.cleanups: list[tuple[str, Callable[[], None]]] = []
        self.restored = False
        self.kernel_touched = False

    def validate_artifact(self, artifact: str, version: str) -> None:
        """Check an exact recovery artifact on every controller before mutation.

        Args:
            artifact (str): Controller-local absolute archive path.
            version (str): Expected metadata application version.
        """
        if not PurePosixPath(artifact).is_absolute() or any(char in artifact for char in "*?[]\n\r"):
            raise ValueError("Audit artifacts require absolute paths without wildcards")
        members = self.keywords.command(f"tar -tf {quote(artifact)}").splitlines()
        matches = [member for member in members if member in ("metadata.yaml", "./metadata.yaml")]
        if len(matches) != 1:
            raise KeywordException(f"Expected one root metadata.yaml in {artifact}")
        metadata = yaml.safe_load(self.keywords.command(f"tar -xOf {quote(artifact)} {quote(matches[0])}"))
        if not isinstance(metadata, dict) or metadata.get("app_name") != "auditd" or str(metadata.get("app_version")) != version:
            raise KeywordException(f"Artifact {artifact} must contain auditd version {version}; found {metadata}")
        checksums = []
        for host in SystemHostListKeywords(self.keywords.ssh_connection).get_controllers():
            checksum = self.keywords.node_command(host.get_host_name(), f"sha256sum -- {quote(artifact)}").split()
            if len(checksum) < 2 or len(checksum[0]) != 64:
                raise KeywordException(f"Invalid artifact checksum on {host.get_host_name()}")
            checksums.append(checksum[0])
        if not checksums or len(set(checksums)) != 1:
            raise KeywordException("Stage the same audit recovery artifact on every controller before testing")

    def capture(self, baseline_artifact: str | None = None) -> AuditdBaseline:
        """Validate and capture a recoverable baseline without changing the lab.

        Applied baselines must already be functional. Uploaded or absent baselines
        may have audit disabled. Missing global parameters and pending reboots are
        rejected because their original effective state cannot be reproduced safely.

        Args:
            baseline_artifact (str | None): Exact original-version archive on all controllers.

        Returns:
            AuditdBaseline: Validated original state.
        """
        if self.baseline is not None:
            raise RuntimeError("Audit baseline has already been captured")
        kw = self.keywords
        with kw.node_session():
            hosts = kw.participating_hosts()
            controller, kernel, application = kw.active_controller(), kw.kernel_parameter(), kw.application_state()
            for hostname in hosts:
                if kw.boot_audit(hostname) != kernel:
                    raise KeywordException(f"Pending/inconsistent audit kernel setting on {hostname}; reconcile before testing")
            overrides, effective = {}, {}
            if application:
                version, status = application
                if status not in ("uploaded", "applied"):
                    raise KeywordException(f"Unsupported audit baseline state: {application}")
                if not baseline_artifact:
                    raise KeywordException("Provide the original-version audit archive before testing an existing app")
                self.validate_artifact(baseline_artifact, version)
                overrides = kw.user_overrides()
                if overrides.get("nameOverride"):
                    raise KeywordException("Baseline nameOverride changes audit pod identity; restore the chart name before testing")
                if status == "applied":
                    kw.verify_runtime(hosts)
                    effective = kw.effective_settings(hosts)
                    persistent = kw.combined_config()
                    if any(settings["config"] != persistent for settings in effective.values()):
                        raise KeywordException("Effective audit config differs from persistent Helm values; reconcile before testing")
            if (application is None or application[1] == "uploaded") and kw.discover_pods():
                raise KeywordException("Audit pods exist without an applied baseline; reconcile orphaned resources before testing")
            self.baseline = AuditdBaseline(hosts, controller, kernel, application, overrides, effective, baseline_artifact)
            return self.baseline

    def add_cleanup(self, description: str, callback: Callable[[], None]) -> None:
        """Register consumer recovery before a test-specific mutation.

        Args:
            description (str): Recovery action identity for diagnostics.
            callback (Callable[[], None]): Idempotent restoration of test-owned changes.
        """
        if self.baseline is None or self.restored:
            raise RuntimeError("Capture an active baseline before registering recovery")
        self.cleanups.append((description, callback))

    def prepare(self, artifact: str | None = None, version: str | None = None) -> None:
        """Enable audit and apply the app, preserving an already applied baseline.

        Args:
            artifact (str | None): Exact install archive when the app is absent.
            version (str | None): Expected install version.
        """
        if self.baseline is None or self.restored:
            raise RuntimeError("Register restoration after capture and before prepare")
        kw, baseline = self.keywords, self.baseline
        if baseline.application is None:
            if not artifact or not version:
                raise KeywordException("An absent audit app requires an artifact and expected version")
            self.validate_artifact(artifact, version)
        if baseline.kernel != "1":
            self.kernel_touched = True
            kw.set_kernel_audit("1", baseline.hosts)
        if baseline.application is None:
            kw.upload(artifact, version)
        if not baseline.application or baseline.application[1] != "applied":
            kw.apply()
        kw.verify_runtime(baseline.hosts)

    def set_overrides(self, values: dict, apply: bool = True) -> None:
        """Replace user values without merging with test leftovers.

        Args:
            values (dict): Complete desired user overrides.
            apply (bool): Apply the application after updating the stored values.
        """
        if self.baseline is None:
            raise RuntimeError("Capture a baseline before modifying overrides")
        kw = self.keywords
        kw.invalidate_node_sessions()
        helm = SystemHelmOverrideKeywords(kw.ssh_connection)
        if values:
            path = f"/tmp/auditd-test-{uuid4().hex}.yaml"
            # The path is owned by this operation and known before any write.
            try:
                kw.command(f"umask 077; printf %s {quote(yaml.safe_dump(values))} > {quote(path)}")
                helm.update_helm_override(path, "auditd", "auditd", "kube-system", reuse_values=False)
            finally:
                kw.command(f"rm -f -- {quote(path)}")
        elif kw.user_overrides():
            helm.delete_system_helm_override("auditd", "auditd", "kube-system")
        if kw.user_overrides() != values:
            raise KeywordException("Audit user overrides did not match the requested mapping")
        if apply:
            kw.apply()

    def _restore_application(self) -> None:
        """Restore original app version, status and exact stored user overrides."""
        kw, baseline = self.keywords, self.baseline
        kw.settle_application()
        current = kw.application_state()
        target = baseline.application
        if current and current[1] not in ("uploaded", "applied", "apply-failed", "remove-failed", "upload-failed"):
            raise KeywordException(f"Audit recovery cannot safely reconcile app state {current}; manual recovery required")
        replace = current and (target is None or current[0] != target[0] or current[1] == "upload-failed")
        if current and (replace or current[1] in ("apply-failed", "remove-failed") or (target and target[1] == "uploaded")):
            if current[1] not in ("uploaded", "upload-failed"):
                kw.remove()
            if replace:
                kw.delete()
                current = None
            else:
                current = (current[0], "uploaded")
        if target is None:
            if kw.application_state() is not None:
                raise KeywordException("Test-created audit application was not deleted")
            return
        if current is None:
            self.validate_artifact(baseline.artifact, target[0])
            kw.upload(baseline.artifact, target[0])
        # Reapply even unchanged stored values: consumers may have changed runtime rules.
        self.set_overrides(baseline.overrides, apply=target[1] == "applied")
        if kw.application_state() != target:
            raise KeywordException(f"Audit application recovery expected {target}, got {kw.application_state()}")

    def _restore_kernel(self) -> None:
        """Restore both configured and booted audit state, even after partial setup."""
        kw, baseline = self.keywords, self.baseline
        with kw.node_session():
            needs_restore = self.kernel_touched or kw.kernel_parameter() != baseline.kernel or any(kw.boot_audit(hostname) != baseline.kernel for hostname in baseline.hosts)
        if needs_restore:
            kw.set_kernel_audit(baseline.kernel, baseline.hosts)
            with kw.node_session():
                for hostname in baseline.hosts:
                    if kw.boot_audit(hostname) != baseline.kernel:
                        raise KeywordException(f"Audit kernel state was not restored on {hostname}")

    def _verify(self) -> None:
        """Verify final inventory and effective settings after recovery."""
        kw, baseline = self.keywords, self.baseline
        with kw.node_session():
            if set(kw.participating_hosts()) != set(baseline.hosts):
                raise KeywordException("Participating host inventory changed during audit testing")
            if kw.application_state() != baseline.application:
                raise KeywordException("Audit application baseline was not restored")
            if (baseline.application is None or baseline.application[1] == "uploaded") and kw.discover_pods():
                raise KeywordException("Audit pods remain after restoring an inactive baseline")
            if baseline.application and kw.user_overrides() != baseline.overrides:
                raise KeywordException("Audit user overrides were not restored")
            if baseline.effective:
                kw.verify_runtime(baseline.hosts)
                if kw.effective_settings(baseline.hosts) != baseline.effective:
                    raise KeywordException("Audit effective settings/rules differ from baseline; manual recovery required")

    def restore(self) -> None:
        """Attempt every recovery stage and report all failures as teardown errors."""
        if self.baseline is None or self.restored:
            return
        errors = []
        stages = list(reversed(self.cleanups))
        if self.baseline.kernel == "1":
            stages.append(("kernel", self._restore_kernel))
        stages += [
            ("application", self._restore_application),
            ("rules", lambda: self.keywords.restore_rules(self.baseline.hosts, self.baseline.effective) if self.baseline.effective else None),
            ("disabled kernel", self._restore_kernel if self.baseline.kernel == "0" else lambda: None),
            ("controller", lambda: self.keywords.restore_controller(self.baseline.controller)),
            ("verification", self._verify),
        ]
        for description, action in stages:
            get_logger().log_info(f"Audit recovery starting: {description}")
            try:
                action()
                get_logger().log_info(f"Audit recovery completed: {description}")
            except Exception as error:
                get_logger().log_warning(f"Audit recovery failed: {description}: {error}")
                errors.append(KeywordException(f"Audit recovery stage {description}: {error}"))
        if errors:
            raise ExceptionGroup("Audit baseline recovery failed; retain logs and recover the reported state manually", errors)
        self.restored = True


def setup_auditd(request: FixtureRequest, prepare: bool = False, options: dict | None = None) -> AuditdState:
    """Capture audit state, register recovery and optionally prepare the app.

    Tests call this lifecycle helper explicitly, following the repository's
    request.addfinalizer pattern. Configuration contains artifact data only;
    the test chooses whether to prepare the app through the prepare argument.

    Args:
        request (FixtureRequest): Test request used to register restoration.
        prepare (bool): Enable audit and apply the app after capturing its state.
        options (dict | None): Artifact/version overrides for this invocation.

    Returns:
        AuditdState: Shared keywords, original baseline and cleanup registration.
    """
    configured = ConfigurationManager.get_app_config().get_auditd_test_options()
    parameters = options if options is not None else {}
    if not isinstance(prepare, bool):
        raise ValueError("prepare must be a boolean")
    allowed = {"baseline_artifact", "artifact", "version"}
    for source, values in (("app configuration auditd_test_options", configured), ("audit setup options", parameters)):
        if not isinstance(values, dict):
            raise ValueError(f"{source} must be a mapping")
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Unknown keys in {source}: {sorted(unknown)}; allowed keys: {sorted(allowed)}")
        for key in ("baseline_artifact", "artifact", "version"):
            if key in values and (not isinstance(values[key], str) or not values[key].strip()):
                raise ValueError(f"{key} in {source} must be a nonempty string")
    options = {**configured, **parameters}
    state = AuditdState(AuditdKeywords(LabConnectionKeywords().get_active_controller_ssh()))
    state.capture(options.get("baseline_artifact"))
    request.addfinalizer(state.restore)
    if prepare:
        state.prepare(options.get("artifact"), options.get("version"))
    return state
