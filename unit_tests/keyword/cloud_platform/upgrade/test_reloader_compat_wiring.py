"""Drive the production reloader compatibility test body with stand-in keywords.

The test case itself cannot run without a lab, so nothing has ever executed its body: the package
glob, the upload, the apply, the finalizer ordering and the per-phase assertions. This drives the
real function with every keyword class patched, which covers the wiring around the reload check
rather than the check itself - ReloaderRestartKeywords has its own tests and is stubbed here.

Shaped after test_audit_compat_wiring.py, which does the same for the auditd compatibility test.
"""

from contextlib import ExitStack
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest

MODULE = "testcases.cloud_platform.upgrade.app_compat.test_reloader_upgrade_compat"

PACKAGE = "/usr/local/share/applications/helm/reloader-26.10-4.tgz"


class ReloaderCompatibilityModel:
    """Stateful stand-ins for every collaborator the production body builds.

    Named for this test case rather than reusing CompatibilityModel, which two other harnesses in
    this directory already define for theirs.
    """

    def __init__(self, release: str = "26.10", target: str = "27.03", present: bool = True, applied: bool = True, package_matches: list = None, alarm_error: str = None, pod_count: int = 2):
        """Build a model that lets the body run to completion unless told otherwise.

        Args:
            release (str): the release the platform reports at the start.
            target (str): the release the config names as the upgrade target.
            present (bool): whether the application is already in the application list.
            applied (bool): whether the application already reports applied.
            package_matches (list): what the package glob returns. Defaults to one match.
            alarm_error (str): when set, the blocking-alarm gate raises with this message.
            pod_count (int): how many pods the namespace reports at baseline.
        """
        self.original_release = release
        self.release = release
        self.target = target
        self.present = present
        self.applied = applied
        self.package_matches = [PACKAGE] if package_matches is None else package_matches
        self.alarm_error = alarm_error
        self.pod_count = pod_count

        # Every collaborator call, in order. The ordering assertions read this.
        self.calls = []
        self.finalizers = []
        self.uploaded = []
        self.applied_calls = []
        self.phases = []
        self.readiness_reads = []
        self.upgrade_kwargs = {}
        self.to_version_keys = []
        # validate_equals raises a bare Exception("Validation Failed"); the description it was given
        # goes to the logger. Captured so the message a failing precondition reports can be asserted.
        self.validation_logger = None

        self.deploy = SimpleNamespace(
            get_running_release=self._running_release,
            get_release_id_for_version=self._release_id,
            deploy_upgrade=self._upgrade,
            deploy_rollback=self._rollback,
        )
        self.health = SimpleNamespace(
            wait_for_app_applied=self._wait_applied,
            is_app_applied=self._is_applied,
            get_app_version=self._app_version,
            get_pod_count=self._pod_count,
            get_not_ready_pod_count=self._not_ready,
            get_app_or_deploy_alarm_count=self._alarm_count,
        )
        self.platform_upgrade = SimpleNamespace(require_no_blocking_alarms=self._require_no_alarms)
        self.recovery = SimpleNamespace(restore_to_release=self._restore)
        self.reload_check = SimpleNamespace(validate_reload_delivers=self._validate_reload)
        self.app_list = SimpleNamespace(get_system_application_list=lambda: SimpleNamespace(is_in_application_list=self._in_list))
        self.app_upload = SimpleNamespace(system_application_upload=self._upload)
        self.app_apply = SimpleNamespace(system_application_apply=self._apply)
        self.ls = SimpleNamespace(get_matching_files=self._matching_files)
        self.config = SimpleNamespace(get_app_name=lambda key: "reloader", get_namespace=lambda key: "reloader", get_to_version=self._to_version)
        self.usm = SimpleNamespace(get_app_applied_timeout_sec=lambda: 1800)
        self.request = SimpleNamespace(addfinalizer=self._add_finalizer)

    # --- collaborator behaviour -------------------------------------------------------------

    def _running_release(self) -> str:
        """Return the release the platform currently reports.

        Returns:
            str: the current release.
        """
        return self.release

    def _release_id(self, version: str) -> str:
        """Resolve a release to an uploaded load id.

        Args:
            version (str): the release to resolve.

        Returns:
            str: the load id.
        """
        self.calls.append("resolve-load")
        return f"starlingx-{version}"

    def _upgrade(self, target: str, leave_at_activate_done: bool = False) -> None:
        """Move the platform to the target release.

        Args:
            target (str): the release to upgrade to.
            leave_at_activate_done (bool): whether the deploy stops at activate-done.
        """
        self.calls.append("upgrade")
        self.upgrade_kwargs = {"target": target, "leave_at_activate_done": leave_at_activate_done}
        self.release = target

    def _rollback(self) -> None:
        """Return the platform to the release it started on."""
        self.calls.append("rollback")
        self.release = self.original_release

    def _wait_applied(self, app: str) -> None:
        """Wait for the application to report applied.

        Args:
            app (str): the application name.
        """
        self.calls.append("wait-applied")

    def _is_applied(self, app: str) -> bool:
        """Report whether the application is applied.

        Args:
            app (str): the application name.

        Returns:
            bool: whether it is applied.
        """
        self.calls.append("is-applied")
        return self.applied

    def _app_version(self, app: str) -> str:
        """Report the application version, which carries the release as its prefix.

        Args:
            app (str): the application name.

        Returns:
            str: the application version.
        """
        return f"{self.release}-4"

    def _pod_count(self, namespace: str) -> int:
        """Report how many pods the namespace holds.

        Args:
            namespace (str): the namespace.

        Returns:
            int: the pod count.
        """
        return self.pod_count

    def _not_ready(self, namespace: str, expected_min: int = 1, label: str = None) -> int:
        """Report how many pods are not ready, recording the floor it was asked to enforce.

        Args:
            namespace (str): the namespace.
            expected_min (int): the minimum pod count the caller requires.
            label (str): an optional label selector.

        Returns:
            int: the not-ready count, always zero here.
        """
        self.readiness_reads.append(expected_min)
        return 0

    def _alarm_count(self) -> int:
        """Report the application and deploy alarm count.

        Returns:
            int: the alarm count, always zero here.
        """
        self.calls.append("alarm-count")
        return 0

    def _require_no_alarms(self) -> None:
        """Refuse to proceed when the environment carries a blocking alarm.

        Raises:
            Exception: when the model was built with an alarm error.
        """
        self.calls.append("alarm-gate")
        if self.alarm_error:
            raise Exception(self.alarm_error)

    def _restore(self, release: str) -> None:
        """Restore the platform to the release the run started on.

        Args:
            release (str): the release to restore.
        """
        self.calls.append("restore-release")

    def _validate_reload(self, request: object, phase: str) -> None:
        """Stand in for the reload check, registering the per-phase cleanup it registers for real.

        The real keyword registers a namespace finalizer before it creates anything, so the stub
        does too. Without that the teardown ordering this harness asserts would be unobservable.

        Args:
            request (object): the pytest request the finalizer is registered against.
            phase (str): the phase label.
        """
        self.calls.append(f"reload-{phase}")
        self.phases.append(phase)
        request.addfinalizer(lambda: self.calls.append(f"cleanup-{phase}"))

    def _in_list(self, app: str) -> bool:
        """Report whether the application appears in the application list.

        Args:
            app (str): the application name.

        Returns:
            bool: whether it is present.
        """
        return self.present

    def _matching_files(self, pattern: str) -> list:
        """Report what the package glob matches.

        Args:
            pattern (str): the glob.

        Returns:
            list: matching paths.
        """
        self.calls.append("package-glob")
        return list(self.package_matches)

    def _upload(self, upload_input: object) -> None:
        """Upload the application package.

        Args:
            upload_input (object): the real upload input object the body built.
        """
        self.calls.append("upload")
        self.uploaded.append(upload_input)

    def _apply(self, app: str, timeout: int = None) -> None:
        """Apply the application.

        Args:
            app (str): the application name.
            timeout (int): the applied timeout the body resolved from configuration.
        """
        self.calls.append("apply")
        self.applied_calls.append(timeout)
        self.applied = True

    def _to_version(self, key: str = None) -> str:
        """Return the configured target release, recording the application key it was asked for.

        The production body calls this with an application key, so the signature takes one. A
        zero-argument stub - which the audit harness uses, because its config read predates the
        per-application override - raises TypeError here.

        Args:
            key (str): the application key, or None for the shared value.

        Returns:
            str: the target release.
        """
        self.to_version_keys.append(key)
        return self.target

    def _add_finalizer(self, finalizer: object) -> None:
        """Register a finalizer, recording the registration order.

        Args:
            finalizer (object): the callable to run at teardown.
        """
        self.calls.append("register-finalizer")
        self.finalizers.append(finalizer)

    # --- driving the production body --------------------------------------------------------

    def run(self) -> None:
        """Execute the production test body with every collaborator replaced."""
        module = import_module(MODULE)
        with ExitStack() as stack:
            for name, value in {
                "SoftwareDeploySequenceKeywords": self.deploy,
                "ApplicationHealthKeywords": self.health,
                "StandardPlatformUpgradeKeywords": self.platform_upgrade,
                "UpgradeRecoveryKeywords": self.recovery,
                "ReloaderRestartKeywords": self.reload_check,
                "SystemApplicationListKeywords": self.app_list,
                "SystemApplicationUploadKeywords": self.app_upload,
                "SystemApplicationApplyKeywords": self.app_apply,
                "LsKeywords": self.ls,
            }.items():
                stack.enter_context(patch.object(module, name, return_value=value))
            stack.enter_context(patch.object(module, "LabConnectionKeywords"))
            stack.enter_context(patch.object(module, "get_logger"))
            self.validation_logger = stack.enter_context(patch("framework.validation.validation.get_logger"))
            stack.enter_context(patch.object(module.ConfigurationManager, "get_app_upgrade_compat_config", return_value=self.config))
            stack.enter_context(patch.object(module.ConfigurationManager, "get_usm_config", return_value=self.usm))
            # The real budgets are 900s and 15s. A failing assertion would spend the whole 900s of
            # wall clock here, so they are shortened for the harness and asserted separately.
            stack.enter_context(patch.object(module, "POD_READY_TIMEOUT", 1))
            stack.enter_context(patch.object(module, "POD_READY_POLL_INTERVAL", 0))
            module.test_reloader_upgrade_rollback(self.request)

    def teardown(self) -> None:
        """Run the registered finalizers the way pytest does, last registered first.

        The logger is patched again here: teardown runs after run() has left its patch context, and
        the production finalizer logs a teardown step.
        """
        module = import_module(MODULE)
        with patch.object(module, "get_logger"):
            for finalizer in reversed(self.finalizers):
                finalizer()


def test_the_body_runs_to_completion():
    """The whole production body executes against stand-ins, which nothing covered before this."""
    model = ReloaderCompatibilityModel()
    model.run()
    assert model.phases == ["pre", "post-upgrade", "post-rollback"]
    assert model.release == model.original_release


def test_the_release_finalizer_is_registered_before_anything_is_created():
    """A setup that fails part way through must still leave the platform on its starting release."""
    model = ReloaderCompatibilityModel(present=False, applied=False)
    model.run()
    assert model.calls.index("register-finalizer") < model.calls.index("upload")
    assert model.calls.index("register-finalizer") < model.calls.index("apply")


def test_the_alarm_gate_runs_before_the_first_mutation_and_again_before_the_upgrade():
    """Pre-existing alarms are attributed to the environment, and ones we raise are caught too.

    The first gate runs before anything is created, so a standing alarm is named rather than
    reported later as an application failure. The second runs after the apply, because an alarm
    raised by our own apply would otherwise first surface as the bare refusal from deploy start.
    """
    model = ReloaderCompatibilityModel(present=False, applied=False)
    model.run()
    gates = [i for i, call in enumerate(model.calls) if call == "alarm-gate"]
    assert len(gates) == 2, f"expected two alarm gates, got {model.calls}"
    assert gates[0] < model.calls.index("upload")
    assert gates[1] > model.calls.index("apply")
    assert gates[1] < model.calls.index("upgrade")


def test_a_blocking_alarm_stops_the_run_before_anything_is_created():
    """The gate's whole purpose is to refuse before mutating, naming what it found."""
    model = ReloaderCompatibilityModel(present=False, applied=False, alarm_error="250.001 (host=controller-0)")
    with pytest.raises(Exception, match="250.001"):
        model.run()
    assert "upload" not in model.calls
    assert "apply" not in model.calls


def test_an_absent_application_with_no_package_fails_the_precondition():
    """Neither the application nor its package present means this release cannot be a baseline."""
    model = ReloaderCompatibilityModel(present=False, package_matches=[])
    with pytest.raises(Exception, match="Validation Failed"):
        model.run()
    assert "upload" not in model.calls
    assert "apply" not in model.calls
    # validate_equals puts the description in the log rather than the exception, so the message a
    # reader of a failed run actually sees is asserted where it is emitted.
    logged = " ".join(str(call) for call in model.validation_logger.return_value.log_error.call_args_list)
    assert "not available on release" in logged, f"the precondition did not name itself: {logged}"


def test_an_absent_application_is_uploaded_from_the_matched_package():
    """The glob's result is what gets uploaded, and the apply follows it."""
    model = ReloaderCompatibilityModel(present=False, applied=False)
    model.run()
    assert model.calls.index("upload") < model.calls.index("apply")
    assert len(model.uploaded) == 1
    assert model.uploaded[0].get_tar_file_path() == PACKAGE


def test_a_present_application_is_not_uploaded_again():
    """Uploading over an application that is already in place is what the guard exists to stop."""
    model = ReloaderCompatibilityModel(present=True, applied=True)
    model.run()
    assert "upload" not in model.calls
    assert "apply" not in model.calls


def test_the_upgrade_is_left_at_activate_done_so_it_can_be_rolled_back():
    """A deploy that completed cannot be rolled back, which is the whole second half of the test."""
    model = ReloaderCompatibilityModel()
    model.run()
    assert model.upgrade_kwargs == {"target": "27.03", "leave_at_activate_done": True}


def test_the_application_is_required_to_be_applied_before_the_upgrade():
    """An application that is not applied is not carried forward by the platform.

    Counted rather than ordered. The setup block reads the applied state too, to decide whether to
    apply, so an assertion that merely puts some read before the upgrade is satisfied by that one
    and cannot fail. The gate is the second read, and it has to sit after the apply.
    """
    model = ReloaderCompatibilityModel(present=False, applied=False)
    model.run()
    reads = [i for i, call in enumerate(model.calls) if call == "is-applied"]
    assert len(reads) == 2, f"expected a setup read and a pre-upgrade gate, got {model.calls}"
    assert reads[1] > model.calls.index("apply")
    assert reads[1] < model.calls.index("upgrade")


def test_the_baseline_pod_count_becomes_the_floor_for_the_later_phases():
    """Later phases require at least as many pods as the baseline had, not merely one.

    The baseline read has no floor to carry yet, so it uses the keyword's own default. Both later
    reads must carry the count observed at baseline, otherwise an application that came back with
    fewer pods than it started with would pass.
    """
    model = ReloaderCompatibilityModel(pod_count=3)
    model.run()
    assert model.readiness_reads == [1, 3, 3], f"readiness floors were {model.readiness_reads}"


def test_the_alarm_count_is_asserted_after_the_upgrade_and_after_the_rollback():
    """Rollback re-applies the application, which is the same event the upgrade check guards."""
    model = ReloaderCompatibilityModel()
    model.run()
    counts = [i for i, call in enumerate(model.calls) if call == "alarm-count"]
    assert len(counts) == 2, f"expected two alarm counts, got {model.calls}"
    assert counts[0] > model.calls.index("upgrade")
    assert counts[1] > model.calls.index("rollback")


def test_the_target_release_is_read_for_this_application_specifically():
    """The per-application override exists only if the application key is passed through."""
    model = ReloaderCompatibilityModel()
    model.run()
    assert model.to_version_keys == ["reloader"]


def test_the_load_is_resolved_before_anything_is_created():
    """Without the target load the run can do nothing, and the baseline phase is slow."""
    model = ReloaderCompatibilityModel(present=False, applied=False)
    model.run()
    assert model.calls.index("resolve-load") < model.calls.index("upload")


def test_teardown_restores_the_starting_release_and_removes_each_phase_namespace():
    """Pins the order teardown actually runs in, which is not the order it was registered in.

    pytest runs finalizers last-registered-first. The release restore is registered before anything
    is created, so it runs last, after the per-phase namespace cleanups. Each phase already removes
    its own namespace on the happy path and marks it done, so at most one cleanup has work to do,
    and the cleanup is tolerant. Recorded here so the order cannot change unnoticed.
    """
    model = ReloaderCompatibilityModel()
    model.run()
    model.teardown()
    tail = [call for call in model.calls if call.startswith("cleanup-") or call == "restore-release"]
    assert tail == ["cleanup-post-rollback", "cleanup-post-upgrade", "cleanup-pre", "restore-release"]


def test_the_real_timeouts_are_the_configured_budgets():
    """The harness shortens the waits, so the shipped values are asserted separately."""
    module = import_module(MODULE)
    assert module.POD_READY_TIMEOUT == 900
    assert module.POD_READY_POLL_INTERVAL == 15
