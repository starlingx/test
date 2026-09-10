"""Unit tests for the USM deploy recovery verbs.

Cover the three rollback verbs without a lab: that each sends the right platform command, that
sudo selects the matching send path, that the configured timeout is applied, and that the output
is reduced to its last non-empty line.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords


class TestUSMDeployRecoveryVerbs(unittest.TestCase):
    """Test suite for software deploy abort / activate-rollback / host-rollback."""

    ACTIVATE_TIMEOUT = 1800
    HOST_TIMEOUT = 3600

    def setUp(self):
        """Silence the BaseKeyword logging wrapper."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()

    def tearDown(self):
        """Stop the logger patcher."""
        self.logger_patcher.stop()

    def _build_keywords(self, output=("Deploy abort has started",)):
        """Return a USMKeywords instance with mocked SSH and config.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock to
        keep that wrapper from replacing them.

        Args:
            output (tuple): lines the SSH send returns.

        Returns:
            tuple: (keywords, ssh mock)
        """
        keywords = USMKeywords.__new__(USMKeywords)

        ssh = NonCallableMagicMock()
        ssh.send = MagicMock(return_value=list(output))
        ssh.send_as_sudo = MagicMock(return_value=list(output))

        usm_config = NonCallableMagicMock()
        usm_config.get_deploy_activate_timeout_sec = MagicMock(return_value=self.ACTIVATE_TIMEOUT)
        usm_config.get_deploy_host_timeout_sec = MagicMock(return_value=self.HOST_TIMEOUT)

        object.__setattr__(keywords, "ssh_connection", ssh)
        object.__setattr__(keywords, "usm_config", usm_config)
        object.__setattr__(keywords, "validate_success_return_code", MagicMock())
        return keywords, ssh

    def test_abort_sends_deploy_abort(self):
        """Abort issues 'software deploy abort' with the activate timeout."""
        keywords, ssh = self._build_keywords()

        result = keywords.software_deploy_abort()

        sent = ssh.send.call_args[0][0]
        self.assertIn("software deploy abort", sent)
        self.assertEqual(ssh.send.call_args[1]["command_timeout"], self.ACTIVATE_TIMEOUT)
        self.assertEqual(result, "Deploy abort has started")

    def test_activate_rollback_sends_activate_rollback(self):
        """Activate-rollback issues 'software deploy activate-rollback'."""
        keywords, ssh = self._build_keywords(output=("Deploy activate-rollback has started",))

        result = keywords.software_deploy_activate_rollback()

        sent = ssh.send.call_args[0][0]
        self.assertIn("software deploy activate-rollback", sent)
        self.assertEqual(result, "Deploy activate-rollback has started")

    def test_host_rollback_includes_host_and_host_timeout(self):
        """Host-rollback names the host and uses the deploy-host timeout."""
        keywords, ssh = self._build_keywords(output=("Host rollback has started",))

        result = keywords.software_deploy_host_rollback("controller-1")

        sent = ssh.send.call_args[0][0]
        self.assertIn("software deploy host-rollback controller-1", sent)
        self.assertEqual(ssh.send.call_args[1]["command_timeout"], self.HOST_TIMEOUT)
        self.assertEqual(result, "Host rollback has started")

    def test_sudo_uses_the_sudo_send_path(self):
        """With sudo=True the command goes through send_as_sudo, not send."""
        keywords, ssh = self._build_keywords()

        keywords.software_deploy_abort(sudo=True)

        ssh.send_as_sudo.assert_called_once()
        ssh.send.assert_not_called()

    def test_output_is_reduced_to_last_non_empty_line(self):
        """Blank lines and trailing whitespace are stripped; the last real line is returned."""
        keywords, _ = self._build_keywords(output=("  ", "first line", "  last line  ", ""))

        result = keywords.software_deploy_abort()

        self.assertEqual(result, "last line")

    def test_empty_output_returns_empty_string(self):
        """No output at all yields an empty string rather than an IndexError."""
        keywords, _ = self._build_keywords(output=())

        result = keywords.software_deploy_abort()

        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
