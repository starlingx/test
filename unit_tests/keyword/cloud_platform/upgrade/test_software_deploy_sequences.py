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

        host_lock.lock_host.assert_called_once_with("controller-0")
        host_lock.unlock_host.assert_called_once_with("controller-0")

    def test_host_is_unlocked_even_when_the_deploy_fails(self):
        """A failing deploy still unlocks the host, so the system is not left wedged."""
        keywords, usm, host_lock, _ = self._build_keywords()
        usm.software_deploy_host = MagicMock(side_effect=KeywordException("deploy host failed"))

        with self.assertRaises(KeywordException):
            keywords.deploy_host_guarded("controller-0")

        host_lock.unlock_host.assert_called_once_with("controller-0")

    def test_active_controller_is_swacted_before_being_locked(self):
        """The swact check runs before the lock, since an active controller cannot be locked."""
        keywords, _, host_lock, host_swact = self._build_keywords()
        order = []
        host_swact.swact_if_active = MagicMock(side_effect=lambda h: order.append("swact"))
        host_lock.lock_host = MagicMock(side_effect=lambda h: order.append("lock"))

        keywords.deploy_host_guarded("controller-0")

        self.assertEqual(order, ["swact", "lock"])

    def test_rollback_flag_selects_the_host_rollback_verb(self):
        """With rollback=True the host is rolled back rather than deployed."""
        keywords, usm, _, _ = self._build_keywords()

        keywords.deploy_host_guarded("controller-0", rollback=True)

        usm.software_deploy_host_rollback.assert_called_once_with("controller-0", sudo=False)
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


if __name__ == "__main__":
    unittest.main()
