"""Unit tests for the SoftwareDeploySequenceKeywords deploy and rollback sequences.

Cover, without a lab: that a host is unlocked even when its deploy fails, that the deploy is
completed only when no rollback will follow, that the rollback runs its full four-step sequence in
order, and that a rollback which already started is resumed from where it reached rather than
restarted from abort.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, call, patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords


class TestSoftwareDeploySequences(unittest.TestCase):
    """Test suite for the multi-step deploy and rollback sequences."""

    def setUp(self):
        """Silence the BaseKeyword logging wrapper."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()

    def tearDown(self):
        """Stop the logger patcher."""
        self.logger_patcher.stop()

    def _build_keywords(self, deploy_state="", hosts=("controller-0",), releases=("starlingx-26.10.0",)):
        """Return an instance with every collaborator mocked and the state guard satisfied.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock to
        keep that wrapper from replacing them.

        Args:
            deploy_state (str): state reported by 'software deploy show'.
            hosts (tuple): hosts returned by deploy_host_upgrade_order, in platform order.
            releases (tuple): release names reported by 'software list'.

        Returns:
            tuple: (keywords, usm mock, host_lock mock, host_order mock)
        """
        keywords = SoftwareDeploySequenceKeywords.__new__(SoftwareDeploySequenceKeywords)

        usm = NonCallableMagicMock()
        usm.wait_for_deploy_state = MagicMock(return_value=True)
        usm.deploy_host_upgrade_order = MagicMock(return_value=list(hosts))

        show_output = NonCallableMagicMock()
        show_output.get_software_deploy_show_details = MagicMock(
            return_value=[{"State": deploy_state}] if deploy_state else []
        )
        show_object = NonCallableMagicMock()
        show_object.get_state = MagicMock(return_value=deploy_state)
        show_output.get_software_deploy_show = MagicMock(return_value=show_object)
        deploy_show = NonCallableMagicMock()
        deploy_show.get_software_deploy_show = MagicMock(return_value=show_output)

        entries = []
        for release in releases:
            entry = NonCallableMagicMock()
            entry.get_release = MagicMock(return_value=release)
            entries.append(entry)
        list_output = NonCallableMagicMock()
        list_output.get_software_lists = MagicMock(return_value=entries)
        software_list = NonCallableMagicMock()
        software_list.get_software_list = MagicMock(return_value=list_output)

        host_lock = NonCallableMagicMock()
        host_swact = NonCallableMagicMock()
        host_swact.swact_if_active = MagicMock(return_value=False)

        alarms = NonCallableMagicMock()
        alarms.alarm_list = MagicMock(return_value=[])

        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        object.__setattr__(keywords, "usm", usm)
        object.__setattr__(keywords, "deploy_show", deploy_show)
        object.__setattr__(keywords, "software_list", software_list)
        object.__setattr__(keywords, "system_show", NonCallableMagicMock())
        object.__setattr__(keywords, "host_lock", host_lock)
        object.__setattr__(keywords, "host_swact", host_swact)
        object.__setattr__(keywords, "alarms", alarms)
        # The async per-host deploy wait hits 'software deploy host-list' on a lab; stub it so the
        # sequence tests stay offline. Its own behaviour is covered by dedicated tests below.
        object.__setattr__(keywords, "_wait_for_host_deploy_done", MagicMock())
        return keywords, usm, host_lock, host_swact

    @staticmethod
    def _alarm(alarm_id, entity_id="host=controller-0"):
        """Return a mocked alarm object.

        Args:
            alarm_id (str): the alarm ID.
            entity_id (str): the entity the alarm is raised against.

        Returns:
            NonCallableMagicMock: stands in for AlarmListObject.
        """
        alarm = NonCallableMagicMock()
        alarm.get_alarm_id = MagicMock(return_value=alarm_id)
        alarm.get_entity_id = MagicMock(return_value=entity_id)
        return alarm

    def test_host_is_unlocked_after_a_successful_deploy(self):
        """The host is locked and unlocked around the deploy."""
        keywords, _, host_lock, _ = self._build_keywords()

        keywords.deploy_host_guarded("controller-0")

        host_lock.lock_host.assert_called_once()
        self.assertEqual(host_lock.lock_host.call_args.args[0], "controller-0")
        host_lock.unlock_host.assert_called_once_with("controller-0", exclude_alarm_ids=None)

    def test_deploy_waits_for_host_deployed_before_unlocking(self):
        """deploy_host_guarded waits for the per-host deployed state before unlocking (async deploy)."""
        keywords, usm, host_lock, _ = self._build_keywords()
        order = []
        usm.software_deploy_host = MagicMock(side_effect=lambda h, **k: order.append("deploy"))
        object.__setattr__(keywords, "_wait_for_host_deploy_done", MagicMock(side_effect=lambda *a, **k: order.append("wait")))
        host_lock.unlock_host = MagicMock(side_effect=lambda h, *a, **k: order.append("unlock"))

        keywords.deploy_host_guarded("controller-0")

        self.assertEqual(order, ["deploy", "wait", "unlock"])

    def test_rollback_waits_for_host_rollback_deployed_before_unlocking(self):
        """On rollback the per-host wait targets the rollback-deployed state before the unlock."""
        keywords, usm, _, _ = self._build_keywords()
        wait = MagicMock()
        object.__setattr__(keywords, "_wait_for_host_deploy_done", wait)

        keywords.deploy_host_guarded("controller-0", rollback=True)

        wait.assert_called_once_with("controller-0", "deploy-host-rollback-deployed")

    def test_host_is_unlocked_even_when_the_deploy_fails(self):
        """A failing deploy still unlocks the host, so the system is not left wedged."""
        keywords, usm, host_lock, _ = self._build_keywords()
        usm.software_deploy_host = MagicMock(side_effect=KeywordException("deploy host failed"))

        with self.assertRaises(KeywordException):
            keywords.deploy_host_guarded("controller-0")

        host_lock.unlock_host.assert_called_once_with("controller-0", exclude_alarm_ids=None)

    def test_deploy_failure_is_not_masked_by_a_failing_recovery_unlock(self):
        """When the deploy fails and the recovery unlock also fails, the original deploy error wins.

        A failed host-rollback leaves the deploy not-completed, so the recovery unlock in the
        finally is rejected and raises its own "failed to unlock" error. That must not replace the
        real deploy failure, otherwise the surfaced error points at the unlock instead of the
        actual host-rollback/host-install failure.
        """
        keywords, usm, host_lock, _ = self._build_keywords()
        usm.software_deploy_host_rollback = MagicMock(side_effect=KeywordException("host-rollback timed out"))
        host_lock.unlock_host = MagicMock(side_effect=KeywordException("Timeout: failed to unlock host controller-0"))

        with patch("keywords.cloud_platform.upgrade.software_deploy_sequence_keywords.get_logger"):
            with self.assertRaises(KeywordException) as raised:
                keywords.deploy_host_guarded("controller-0", rollback=True)

        self.assertIn("host-rollback timed out", str(raised.exception))
        host_lock.unlock_host.assert_called_once_with("controller-0", exclude_alarm_ids=["250.001"])

    def test_rollback_unlock_excludes_config_out_of_date_but_forward_does_not(self):
        """The rollback unlock ignores 250.001 (expected until the peer rolls); a forward unlock does not.

        On an AIO-DX the first controller to roll back carries a config-out-of-date alarm that only
        clears once its peer also rolls - the very next step - so blocking the unlock on it is a
        circular stall. The exclusion is scoped to the rollback unlock; a forward deploy keeps the
        default blocking behaviour.
        """
        keywords, _, host_lock, _ = self._build_keywords()
        keywords.deploy_host_guarded("controller-0", rollback=True)
        self.assertEqual(host_lock.unlock_host.call_args.kwargs.get("exclude_alarm_ids"), ["250.001"])

        keywords, _, host_lock, _ = self._build_keywords()
        keywords.deploy_host_guarded("controller-0", rollback=False)
        self.assertIsNone(host_lock.unlock_host.call_args.kwargs.get("exclude_alarm_ids"))

    def test_active_controller_is_swacted_before_being_locked(self):
        """The swact check runs before the lock, since an active controller cannot be locked."""
        keywords, _, host_lock, host_swact = self._build_keywords()
        order = []
        host_swact.swact_if_active = MagicMock(side_effect=lambda h: order.append("swact"))
        host_lock.lock_host = MagicMock(side_effect=lambda h, *a, **k: order.append("lock"))

        keywords.deploy_host_guarded("controller-0")

        self.assertEqual(order, ["swact", "lock"])

    def test_rollback_flag_selects_the_host_rollback_verb(self):
        """With rollback=True the host is rolled back rather than deployed."""
        keywords, usm, _, _ = self._build_keywords()

        keywords.deploy_host_guarded("controller-0", rollback=True)

        usm.software_deploy_host_rollback.assert_called_once()
        call = usm.software_deploy_host_rollback.call_args
        self.assertEqual(call.args[0], "controller-0")
        self.assertEqual(call.kwargs.get("sudo"), False)
        self.assertGreater(call.kwargs.get("retries", 0), 0)
        usm.software_deploy_host.assert_not_called()

    def test_upgrade_completes_the_deploy_when_no_rollback_follows(self):
        """An upgrade-only run issues 'deploy complete' so no deploy is left open."""
        keywords, usm, _, _ = self._build_keywords()

        keywords.deploy_upgrade("26.10", leave_at_activate_done=False)

        usm.software_deploy_complete.assert_called_once()

    def test_upgrade_stops_at_activate_done_when_a_rollback_follows(self):
        """A run that will roll back leaves the deploy at activate-done, keeping abort available."""
        keywords, usm, _, _ = self._build_keywords()

        keywords.deploy_upgrade("26.10", leave_at_activate_done=True)

        usm.software_deploy_complete.assert_not_called()

    def test_upgrade_resolves_the_release_id_before_starting(self):
        """'deploy start' receives the full release ID, not the short configured version."""
        keywords, usm, _, _ = self._build_keywords(releases=("starlingx-26.03.0", "starlingx-26.10.0"))

        keywords.deploy_upgrade("26.10", leave_at_activate_done=True)

        usm.deploy_start.assert_called_once_with("starlingx-26.10.0", sudo=False)

    def test_upgrade_stops_when_a_deploy_state_is_not_reached(self):
        """A failed deploy start raises before any host is locked."""
        keywords, usm, host_lock, _ = self._build_keywords(deploy_state="deploy-start-failed")
        usm.wait_for_deploy_state = MagicMock(return_value=False)

        with self.assertRaises(KeywordException):
            keywords.deploy_upgrade("26.10", leave_at_activate_done=True)

        host_lock.lock_host.assert_not_called()

    def test_upgrade_refuses_to_start_with_an_active_alarm(self):
        """An active alarm stops the run before 'deploy start', which would reject it anyway."""
        keywords, usm, _, _ = self._build_keywords()
        keywords.alarms.alarm_list = MagicMock(
            return_value=[self._alarm("500.200", "namespace=stxtest-certmgr")]
        )

        with self.assertRaises(KeywordException) as raised:
            keywords.deploy_upgrade("26.10", leave_at_activate_done=True)

        usm.deploy_start.assert_not_called()
        self.assertIn("500.200", str(raised.exception))
        self.assertIn("stxtest-certmgr", str(raised.exception))

    def test_upgrade_names_every_blocking_alarm(self):
        """All active alarms are reported, not just the first, so one pass shows the full picture."""
        keywords, _, _, _ = self._build_keywords()
        keywords.alarms.alarm_list = MagicMock(
            return_value=[self._alarm("500.200"), self._alarm("750.003")]
        )

        with self.assertRaises(KeywordException) as raised:
            keywords.deploy_upgrade("26.10", leave_at_activate_done=True)

        self.assertIn("500.200", str(raised.exception))
        self.assertIn("750.003", str(raised.exception))
        self.assertIn("2 active alarm", str(raised.exception))

    def test_rollback_runs_the_full_four_step_sequence_in_order(self):
        """Abort, activate-rollback, per-host rollback and delete run in that order."""
        keywords, usm, _, _ = self._build_keywords()
        order = []
        usm.software_deploy_abort = MagicMock(side_effect=lambda **k: order.append("abort"))
        usm.software_deploy_activate_rollback = MagicMock(side_effect=lambda **k: order.append("activate-rollback"))
        usm.software_deploy_host_rollback = MagicMock(side_effect=lambda h, **k: order.append("host-rollback"))
        usm.software_deploy_delete = MagicMock(side_effect=lambda **k: order.append("delete"))

        keywords.deploy_rollback()

        self.assertEqual(order, ["abort", "activate-rollback", "host-rollback", "delete"])

    def test_rollback_waits_for_each_state_it_depends_on(self):
        """Each rollback step waits for the state the next one requires."""
        keywords, usm, _, _ = self._build_keywords()

        keywords.deploy_rollback()

        usm.wait_for_deploy_state.assert_has_calls(
            [
                call("deploy-activate-rollback-pending"),
                call("deploy-activate-rollback-done"),
                call("deploy-host-rollback-done"),
            ]
        )

    def test_resume_from_pending_does_not_reissue_abort(self):
        """Resuming from activate-rollback-pending continues rather than restarting from abort."""
        keywords, usm, _, _ = self._build_keywords(deploy_state="deploy-activate-rollback-pending")

        keywords.resume_partial_rollback()

        usm.software_deploy_abort.assert_not_called()
        usm.software_deploy_activate_rollback.assert_called_once()
        usm.software_deploy_delete.assert_called_once()

    def test_resume_from_activate_rollback_done_skips_to_hosts(self):
        """Resuming from activate-rollback-done rolls hosts back without re-activating."""
        keywords, usm, _, _ = self._build_keywords(deploy_state="deploy-activate-rollback-done")

        keywords.resume_partial_rollback()

        usm.software_deploy_activate_rollback.assert_not_called()
        usm.software_deploy_host_rollback.assert_called_once()
        usm.software_deploy_delete.assert_called_once()

    def test_resume_from_host_rollback_done_only_finalises(self):
        """Resuming from host-rollback-done only issues the finalising delete."""
        keywords, usm, _, _ = self._build_keywords(deploy_state="deploy-host-rollback-done")

        keywords.resume_partial_rollback()

        usm.software_deploy_host_rollback.assert_not_called()
        usm.software_deploy_delete.assert_called_once()

    def test_resume_leaves_a_failed_state_alone(self):
        """An unverified state is left untouched rather than driving untested recovery."""
        keywords, usm, _, _ = self._build_keywords(deploy_state="deploy-activate-rollback-failed")

        keywords.resume_partial_rollback()

        usm.software_deploy_activate_rollback.assert_not_called()
        usm.software_deploy_host_rollback.assert_not_called()
        usm.software_deploy_delete.assert_not_called()

    # ---- per-host lock uses the shared keyword's opt-in retry ----

    def test_deploy_host_locks_with_retry_opt_in(self):
        """deploy_host_guarded locks via lock_host's opt-in retry, not a single no-retry lock.

        The transient-'system host-lock'-error retry now lives in the shared SystemHostLockKeywords
        keyword as an opt-in (retries>0); the deploy flow is the caller that opts in. The detailed
        retry behaviour is covered by the SystemHostLockKeywords unit tests.
        """
        keywords, usm, host_lock, _ = self._build_keywords()
        keywords.deploy_host_guarded("controller-0")
        self.assertEqual(host_lock.lock_host.call_count, 1)
        call = host_lock.lock_host.call_args
        self.assertEqual(call.args[0], "controller-0")
        self.assertGreater(call.kwargs.get("retries", 0), 0)

    # ---- _wait_for_host_deploy_done (async per-host deploy wait before unlock) ----

    MODULE = "keywords.cloud_platform.upgrade.software_deploy_sequence_keywords"

    def _wait_only_keywords(self):
        """Return an instance with just an ssh connection for _wait_for_host_deploy_done tests."""
        keywords = SoftwareDeploySequenceKeywords.__new__(SoftwareDeploySequenceKeywords)
        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        return keywords

    def _host_list_kw(self, states):
        """Return a mock SoftwareDeployHostListKeywords whose get_state_by_host yields the states."""
        out = NonCallableMagicMock()
        out.get_state_by_host = MagicMock(side_effect=states)
        kw = NonCallableMagicMock()
        kw.get_software_deploy_host_list = MagicMock(return_value=out)
        return kw

    def test_wait_for_host_deploy_done_returns_when_deployed(self):
        """Returns once the host's per-host state reaches the deployed state."""
        keywords = self._wait_only_keywords()
        host_list_kw = self._host_list_kw(["deploy-host", "deploy-host", "deploy-host-deployed"])
        with patch(f"{self.MODULE}.SoftwareDeployHostListKeywords", return_value=host_list_kw), \
                patch(f"{self.MODULE}.get_logger"), patch("framework.validation.validation.get_logger"):
            keywords._wait_for_host_deploy_done("controller-0", "deploy-host-deployed", timeout=30, poll_interval=0)

    def test_wait_for_host_deploy_done_raises_on_failed_state(self):
        """A 'failed' per-host state raises immediately rather than waiting out the timeout."""
        keywords = self._wait_only_keywords()
        host_list_kw = self._host_list_kw(["deploy-host-failed"])
        with patch(f"{self.MODULE}.SoftwareDeployHostListKeywords", return_value=host_list_kw), \
                patch(f"{self.MODULE}.get_logger"), patch("framework.validation.validation.get_logger"):
            with self.assertRaises(KeywordException):
                keywords._wait_for_host_deploy_done("controller-0", "deploy-host-deployed", timeout=30, poll_interval=0)


if __name__ == "__main__":
    unittest.main()
