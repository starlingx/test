"""Unit tests for SystemApplicationApplyKeywords.wait_for_applied.

system_application_apply(wait_for_applied=True) waits after issuing an apply, but nothing waits for
an application the platform re-applies by itself after 'software deploy activate'. wait_for_applied
polls the reported status with a budget long enough for that post-activate re-apply. These tests
drive it with the status read and the retry validator mocked, so no live system is required.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords

MODULE = "keywords.cloud_platform.system.application.system_application_apply_keywords"


class TestWaitForApplied(unittest.TestCase):
    """Test suite for the post-activate applied wait."""

    APP_APPLIED_TIMEOUT = 2400

    def setUp(self):
        """Silence the BaseKeyword logger."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()

    def tearDown(self):
        """Stop the logger patcher."""
        self.logger_patcher.stop()

    def _build_keywords(self) -> SystemApplicationApplyKeywords:
        """Return an instance with a mocked SSH connection.

        Returns:
            SystemApplicationApplyKeywords: the instance under test.
        """
        keywords = SystemApplicationApplyKeywords.__new__(SystemApplicationApplyKeywords)
        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        return keywords

    def test_wait_for_applied_uses_the_configured_timeout_by_default(self):
        """With no explicit timeout, the configured application-applied budget is used."""
        keywords = self._build_keywords()

        usm_config = NonCallableMagicMock()
        usm_config.get_app_applied_timeout_sec = MagicMock(return_value=self.APP_APPLIED_TIMEOUT)
        with patch(f"{MODULE}.ConfigurationManager") as config_manager:
            config_manager.get_usm_config = MagicMock(return_value=usm_config)
            with patch(f"{MODULE}.SystemApplicationShowKeywords"):
                with patch(f"{MODULE}.validate_equals_with_retry") as validate:
                    keywords.wait_for_applied("portieris")

        self.assertEqual(validate.call_args[1]["timeout"], self.APP_APPLIED_TIMEOUT)

    def test_wait_for_applied_honours_an_explicit_timeout(self):
        """An explicit timeout overrides the configured default."""
        keywords = self._build_keywords()

        with patch(f"{MODULE}.SystemApplicationShowKeywords"):
            with patch(f"{MODULE}.validate_equals_with_retry") as validate:
                keywords.wait_for_applied("portieris", timeout=60)

        self.assertEqual(validate.call_args[1]["timeout"], 60)


if __name__ == "__main__":
    unittest.main()
