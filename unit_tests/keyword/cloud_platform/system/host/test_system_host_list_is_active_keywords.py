"""Unit tests for SystemHostListKeywords.is_active_controller.

The platform refuses to lock an active controller, so a deploy asks which host is active before
locking. is_active_controller answers that from the active-controller read. These tests mock that
read so no live system is required.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class TestIsActiveController(unittest.TestCase):
    """Test suite for recognising the active controller."""

    def setUp(self):
        """Silence the BaseKeyword logger."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()

    def tearDown(self):
        """Stop the logger patcher."""
        self.logger_patcher.stop()

    def _build_keywords(self, active="controller-0"):
        """Return an instance whose active-controller read reports the given host.

        Args:
            active (str): hostname reported as the active controller.

        Returns:
            SystemHostListKeywords: the instance under test.
        """
        keywords = SystemHostListKeywords.__new__(SystemHostListKeywords)
        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        active_host = NonCallableMagicMock()
        active_host.get_host_name = MagicMock(return_value=active)
        object.__setattr__(keywords, "get_active_controller", MagicMock(return_value=active_host))
        return keywords

    def test_active_controller_is_recognised(self):
        """The host reported as active reads as the active controller."""
        keywords = self._build_keywords(active="controller-0")

        self.assertTrue(keywords.is_active_controller("controller-0"))

    def test_a_non_active_host_is_not_the_active_controller(self):
        """A host that is not the active controller reads as not active."""
        keywords = self._build_keywords(active="controller-0")

        self.assertFalse(keywords.is_active_controller("controller-1"))


if __name__ == "__main__":
    unittest.main()
