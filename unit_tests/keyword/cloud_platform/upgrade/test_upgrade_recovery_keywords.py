"""Unit tests for UpgradeRecoveryKeywords.

Cover the teardown recovery without a lab: that a system already back on its starting release is
left alone, that a full rollback runs from activate-done, that a partial rollback is resumed rather
than restarted, that an unverified deploy state is left in place, that a removed application is
re-applied, and that a failure inside the teardown never propagates and mask the test's own failure.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.upgrade.upgrade_recovery_keywords import UpgradeRecoveryKeywords


class TestUpgradeRecoveryKeywords(unittest.TestCase):
    """Test suite for returning a system to its starting release after an upgrade test."""

    def setUp(self):
        """Silence the BaseKeyword and module loggers."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()
        self.module_logger_patcher = patch(
            "keywords.cloud_platform.upgrade.upgrade_recovery_keywords.get_logger"
        )
        self.module_logger_patcher.start()

    def tearDown(self):
        """Stop the logger patchers."""
        self.logger_patcher.stop()
        self.module_logger_patcher.stop()

    def _build_keywords(self, deploy_state="", running="26.03", app_applied=True):
        """Return an instance whose deploy, health and apply collaborators are mocked.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock to
        keep that wrapper from replacing them.

        Args:
            deploy_state (str): state reported by 'software deploy show'.
            running (str): release the host reports running.
            app_applied (bool): whether the application reads as applied.

        Returns:
            tuple: (keywords, deploy mock, app_apply mock)
        """
        keywords = UpgradeRecoveryKeywords.__new__(UpgradeRecoveryKeywords)

        deploy = NonCallableMagicMock()
        deploy.get_current_deploy_state = MagicMock(return_value=deploy_state)
        deploy.get_running_release = MagicMock(return_value=running)

        health = NonCallableMagicMock()
        health.is_app_applied = MagicMock(return_value=app_applied)

        app_apply = NonCallableMagicMock()

        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        object.__setattr__(keywords, "deploy", deploy)
        object.__setattr__(keywords, "health", health)
        object.__setattr__(keywords, "app_apply", app_apply)
        return keywords, deploy, app_apply

    def test_no_action_when_already_on_the_starting_release(self):
        """A system back on its starting release with no open deploy is left untouched."""
        keywords, deploy, _ = self._build_keywords(deploy_state="", running="26.03")

        keywords.restore_to_release("26.03")

        deploy.deploy_rollback.assert_not_called()
        deploy.resume_partial_rollback.assert_not_called()

    def test_full_rollback_from_activate_done(self):
        """An upgraded system awaiting rollback is rolled back."""
        keywords, deploy, _ = self._build_keywords(deploy_state="deploy-activate-done", running="26.10")

        keywords.restore_to_release("26.03")

        deploy.deploy_rollback.assert_called_once()
        deploy.resume_partial_rollback.assert_not_called()

    def test_partial_rollback_is_resumed_not_restarted(self):
        """A rollback already under way is resumed, since abort is invalid from there."""
        keywords, deploy, _ = self._build_keywords(
            deploy_state="deploy-activate-rollback-done", running="26.10"
        )

        keywords.restore_to_release("26.03")

        deploy.resume_partial_rollback.assert_called_once()
        deploy.deploy_rollback.assert_not_called()

    def test_unverified_state_is_left_in_place(self):
        """A failed deploy state is left alone rather than driving untested recovery."""
        keywords, deploy, _ = self._build_keywords(deploy_state="deploy-host-failed", running="26.10")

        keywords.restore_to_release("26.03")

        deploy.deploy_rollback.assert_not_called()
        deploy.resume_partial_rollback.assert_not_called()

    def test_removed_application_is_reapplied(self):
        """An application the test removed is re-applied so the lab stays usable."""
        keywords, _, app_apply = self._build_keywords(running="26.03", app_applied=False)

        keywords.restore_to_release("26.03", app_name="portieris", app_was_removed=True)

        app_apply.system_application_apply.assert_called_once_with("portieris")

    def test_application_not_reapplied_when_already_applied(self):
        """An application that is already applied is not re-applied."""
        keywords, _, app_apply = self._build_keywords(running="26.03", app_applied=True)

        keywords.restore_to_release("26.03", app_name="portieris", app_was_removed=True)

        app_apply.system_application_apply.assert_not_called()

    def test_application_not_reapplied_when_the_test_did_not_remove_it(self):
        """An application the test never removed is left alone."""
        keywords, _, app_apply = self._build_keywords(running="26.03", app_applied=False)

        keywords.restore_to_release("26.03", app_name="portieris", app_was_removed=False)

        app_apply.system_application_apply.assert_not_called()

    def test_teardown_failure_does_not_propagate(self):
        """A dead SSH session during teardown must not replace the test's real failure."""
        keywords, deploy, _ = self._build_keywords()
        deploy.get_current_deploy_state = MagicMock(side_effect=OSError("socket is closed"))

        keywords.restore_to_release("26.03")


if __name__ == "__main__":
    unittest.main()
