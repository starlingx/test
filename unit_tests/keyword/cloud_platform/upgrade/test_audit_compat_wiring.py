"""Production compatibility setup, phase and ordered recovery contracts."""

from contextlib import ExitStack
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from framework.exceptions.keyword_exception import KeywordException

MODULE = "testcases.cloud_platform.upgrade.app_compat.test_audit_upgrade_compat"


class CompatibilityModel:
    """Drive the real test with stateful platform and audit collaborators."""

    def __init__(self, release="26.03", application=None, audit="0", target="26.10", failure=None):
        self.original_release = release
        self.release = release
        self.target = target
        self.application = application
        self.original_application = application
        self.audit = audit
        self.original_audit = audit
        self.failure = failure
        self.deploy_state = ""
        self.hosts = ("controller-0", "controller-1", "worker-0")
        self.calls = []
        self.finalizers = []
        self.rollback_version = f"{release}-original"
        self.setup = SimpleNamespace(capture=self.capture, prepare=self.prepare_audit, restore=self.restore_audit)
        self.deploy = SimpleNamespace(get_running_release=lambda: self.release, get_current_deploy_state=lambda: self.deploy_state)
        self.driver = SimpleNamespace(require_no_blocking_alarms=self.check_alarms, upgrade_platform_in_order=self.upgrade, rollback_platform_in_order=self.rollback)
        self.preparation = SimpleNamespace(prepare=self.prepare_platform, require_precheck=self.precheck)
        self.recovery = SimpleNamespace(restore_to_release=self.restore_release)
        self.health = SimpleNamespace(wait_for_app_applied=self.require_applied, get_app_version=self.app_version, get_app_or_deploy_alarm_count=lambda: 0)
        self.config = SimpleNamespace(get_app_name=lambda key: "auditd", get_to_version=lambda: self.target)
        self.request = SimpleNamespace(addfinalizer=self.finalizers.append)

    def check_alarms(self):
        """Fail unrelated alarms before setup mutation."""
        self.calls.append("alarms")
        if self.failure == "alarm":
            raise KeywordException("NTP alarm remains")

    def capture(self, release):
        """Record the baseline before either preparation step."""
        assert release == self.original_release
        assert self.application == self.original_application and self.audit == self.original_audit
        self.calls.append("capture")
        return SimpleNamespace(hosts=self.hosts)

    def prepare_platform(self, target):
        """Require both finalizers before touching platform prerequisites."""
        assert target == self.target and len(self.finalizers) == 2
        self.calls.append("platform preparation")
        if self.failure == "platform preparation":
            raise KeywordException("missing upload source")

    def prepare_audit(self):
        """Model partial audit setup, including a response lost after mutation."""
        assert len(self.finalizers) == 2
        self.calls.append("audit preparation")
        self.audit = "1"
        self.application = (f"{self.original_release}-original", "applied")
        if self.failure == "audit preparation":
            raise KeywordException("injected setup failure after mutation")

    def require_applied(self, app):
        """Require prepared applied state at every phase."""
        assert app == "auditd" and self.application[1] == "applied"

    def app_version(self, app):
        """Read the application state changed by upgrade/rollback."""
        assert app == "auditd"
        return self.application[0]

    def capture_event(self, request, phase, hosts):
        """Exercise phase callbacks and register artifact cleanup ahead of recovery."""
        assert hosts == self.hosts and request is self.request and self.audit == "1"
        assert self.release == (self.target if phase == "post-upgrade" else self.original_release)
        self.calls.append(phase)
        request.addfinalizer(lambda: self.calls.append(f"artifact {phase}"))
        if phase == self.failure:
            raise KeywordException("injected functional failure")

    def precheck(self, target):
        """Require the functional baseline before the final deploy precheck."""
        assert target == self.target and self.calls[-1] == "pre"
        self.calls.append("precheck")
        if self.failure == "precheck":
            raise KeywordException("target precheck failed")

    def upgrade(self, sequence, target, leave_at_activate_done):
        """Change both platform and app only after preparation and precheck."""
        assert sequence is self.deploy and target == self.target and leave_at_activate_done
        assert self.calls[-1] == "precheck" and self.audit == "1"
        self.calls.append("upgrade")
        self.release = target
        self.deploy_state = "deploy-activate-done"
        self.application = (f"{target}-target", "applied")

    def rollback(self, sequence):
        """Restore the prepared audit baseline before original-state restoration."""
        assert sequence is self.deploy
        self.calls.append("rollback")
        self.release = self.original_release
        self.deploy_state = ""
        self.application = (self.rollback_version, "applied")

    def restore_release(self, release):
        """Model successful or deliberately incomplete best-effort platform recovery."""
        assert release == self.original_release
        self.calls.append("restore release")
        if self.failure == "release recovery":
            return
        if self.failure == "open deploy recovery":
            self.release = self.original_release
            self.deploy_state = "deploy-host-rollback-failed"
            return
        self.release = release
        self.deploy_state = ""

    def restore_audit(self):
        """Prohibit app/kernel restoration until platform recovery has finished."""
        assert self.release == self.original_release and not self.deploy_state
        assert self.calls[-1] == "restore release"
        self.calls.append("restore audit")
        self.application, self.audit = self.original_application, self.original_audit

    def run(self):
        """Execute the production body without invoking lab configuration or SSH."""
        module = import_module(MODULE)
        with ExitStack() as stack:
            for name, value in {
                "SoftwareDeploySequenceKeywords": self.deploy,
                "StandardPlatformUpgradeKeywords": self.driver,
                "UpgradeRecoveryKeywords": self.recovery,
                "ApplicationHealthKeywords": self.health,
                "AuditEventCaptureKeywords": SimpleNamespace(validate_event_capture=self.capture_event),
                "AuditUpgradeSetupKeywords": self.setup,
                "PlatformUpgradePreparationKeywords": self.preparation,
            }.items():
                constructor = stack.enter_context(patch.object(module, name, return_value=value))
                if name == "UpgradeRecoveryKeywords":
                    recovery_constructor = constructor
            stack.enter_context(patch.object(module, "LabConnectionKeywords"))
            stack.enter_context(patch.object(module, "get_logger"))
            stack.enter_context(patch("framework.validation.validation.get_logger"))
            stack.enter_context(patch.object(module.ConfigurationManager, "get_app_upgrade_compat_config", return_value=self.config))
            module.test_audit_upgrade_rollback(self.request)
            assert recovery_constructor.call_args.kwargs["platform_upgrade"] is self.driver

    def teardown(self):
        """Execute pytest's reverse finalizer order."""
        for finalizer in reversed(self.finalizers):
            finalizer()


@pytest.mark.parametrize("release", ["25.09", "26.03"])
@pytest.mark.parametrize("baseline", ["absent", "uploaded", "applied"])
def test_preparation_and_complete_original_state_restore(release: str, baseline: str) -> None:
    """Prepare each supported baseline and restore it only after platform recovery.

    Args:
        release (str): Installed platform release.
        baseline (str): Original app state.
    """
    original = None if baseline == "absent" else (f"{release}-original", baseline)
    model = CompatibilityModel(release, original, "1" if baseline == "applied" else "0")
    model.run()
    assert model.calls == ["alarms", "capture", "platform preparation", "audit preparation", "pre", "precheck", "upgrade", "post-upgrade", "rollback", "post-rollback"]
    model.teardown()
    assert model.calls[-5:] == ["artifact post-rollback", "artifact post-upgrade", "artifact pre", "restore release", "restore audit"]
    assert (model.application, model.audit) == (original, model.original_audit)


@pytest.mark.parametrize("failure", ["platform preparation", "audit preparation", "pre", "precheck", "post-upgrade"])
def test_failure_paths_restore_original_state(failure: str) -> None:
    """Recover failures before setup, after partial setup and after upgrade.

    Args:
        failure (str): Injected failure stage.
    """
    model = CompatibilityModel(failure=failure)
    with pytest.raises(KeywordException):
        model.run()
    model.teardown()
    assert model.calls[-2:] == ["restore release", "restore audit"]
    assert model.application is None and model.audit == "0"


@pytest.mark.parametrize("failure", ["release recovery", "open deploy recovery"])
def test_incomplete_platform_recovery_preserves_audit_state(failure: str) -> None:
    """Never restore audit under the wrong release or an outstanding deploy.

    Args:
        failure (str): Best-effort recovery failure.
    """
    model = CompatibilityModel()
    model.failure = "post-upgrade"
    with pytest.raises(KeywordException):
        model.run()
    model.failure = failure
    with pytest.raises(KeywordException, match="recovery is incomplete"):
        model.teardown()
    assert "restore audit" not in model.calls and model.audit == "1"


@pytest.mark.parametrize("target", ["26.03", "25.09", None, "invalid"])
def test_invalid_start_target_pair_fails_before_mutations(target: str | None) -> None:
    """Do not reboot or prepare artifacts for an equal, older or malformed target.

    Args:
        target (str | None): Unsupported target.
    """
    model = CompatibilityModel(target=target)
    with pytest.raises((ValueError, KeywordException)):
        model.run()
    assert not model.calls and not model.finalizers


@pytest.mark.parametrize("obstacle", ["open deployment", "alarm"])
def test_unrelated_lab_blocker_is_not_suppressed(obstacle: str) -> None:
    """Stop before setup when a prior deployment or environmental alarm exists.

    Args:
        obstacle (str): Existing lab problem.
    """
    model = CompatibilityModel(failure="alarm" if obstacle == "alarm" else None)
    if obstacle == "open deployment":
        model.deploy_state = "deploy-host-failed"
    with pytest.raises(KeywordException):
        model.run()
    assert "capture" not in model.calls and not model.finalizers


def test_exact_original_application_version_is_required() -> None:
    """Reject a different app build on the correct rolled-back platform release."""
    model = CompatibilityModel()
    model.rollback_version = "26.03-wrong-build"
    with pytest.raises(Exception, match="Validation Failed"):
        model.run()
    assert model.calls[-1] == "rollback"
    model.teardown()
