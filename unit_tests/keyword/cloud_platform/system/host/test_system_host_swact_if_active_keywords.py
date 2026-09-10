"""Unit tests for SystemHostSwactKeywords.swact_if_active.

A deploy locks one host at a time, and the platform refuses to lock an active controller, so a
deploy swacts away from it first. swact_if_active performs that swact only when needed and waits for
it to settle, and skips it on a single-controller system where there is nothing to swact to. These
tests cover that logic with the host-list and swact collaborators mocked.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords

MODULE = "keywords.cloud_platform.system.host.system_host_swact_keywords"


class TestSwactIfActive(unittest.TestCase):
    """Test suite for swacting away from a host before it is locked."""

    def setUp(self):
        """Silence the BaseKeyword and module loggers."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()
        self.module_logger_patcher = patch(f"{MODULE}.get_logger")
        self.module_logger_patcher.start()

    def tearDown(self):
        """Stop the logger patchers."""
        self.logger_patcher.stop()
        self.module_logger_patcher.stop()

    def _build_keywords(self, active="controller-0", standby="controller-1"):
        """Return an instance with the internal host-list and its own swact methods mocked.

        swact_if_active constructs a SystemHostListKeywords from the ssh connection, so that class is
        patched at the module level. host_swact and wait_for_swact are the instance's own methods,
        replaced with mocks via object.__setattr__ to bypass the BaseKeyword logging wrapper.

        Args:
            active (str): hostname reported as the active controller.
            standby (str): hostname reported as the standby controller, or None to make
                get_standby_controller raise as it does on a single-controller system.

        Returns:
            tuple: (keywords, host_list mock, patcher for SystemHostListKeywords)
        """
        keywords = SystemHostSwactKeywords.__new__(SystemHostSwactKeywords)
        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        self.host_swact_mock = MagicMock(return_value=True)
        self.wait_for_swact_mock = MagicMock()
        object.__setattr__(keywords, "host_swact", self.host_swact_mock)
        object.__setattr__(keywords, "wait_for_swact", self.wait_for_swact_mock)

        active_host = NonCallableMagicMock()
        active_host.get_host_name = MagicMock(return_value=active)

        host_list = NonCallableMagicMock()
        host_list.is_active_controller = MagicMock(return_value=(active == "controller-0"))
        host_list.get_active_controller = MagicMock(return_value=active_host)
        if standby is None:
            host_list.get_standby_controller = MagicMock(
                side_effect=KeywordException("No standby controller found")
            )
        else:
            standby_host = NonCallableMagicMock()
            standby_host.get_host_name = MagicMock(return_value=standby)
            host_list.get_standby_controller = MagicMock(return_value=standby_host)

        patcher = patch(f"{MODULE}.SystemHostListKeywords", return_value=host_list)
        return keywords, host_list, patcher

    def test_swact_is_skipped_for_a_standby_host(self):
        """No swact is issued when the host about to be locked is not active."""
        keywords, host_list, patcher = self._build_keywords()
        host_list.is_active_controller = MagicMock(return_value=False)

        with patcher:
            performed = keywords.swact_if_active("controller-1")

        self.assertFalse(performed)
        self.host_swact_mock.assert_not_called()

    def test_swact_is_performed_and_waited_for_on_the_active_host(self):
        """Locking the active controller swacts first and waits for the swact to settle."""
        keywords, host_list, patcher = self._build_keywords()
        host_list.is_active_controller = MagicMock(return_value=True)

        with patcher:
            performed = keywords.swact_if_active("controller-0")

        self.assertTrue(performed)
        self.host_swact_mock.assert_called_once()
        self.wait_for_swact_mock.assert_called_once()

    def test_swact_waits_after_issuing_not_before(self):
        """wait_for_swact is called after host_swact, so the lock cannot race the role switch."""
        keywords, host_list, patcher = self._build_keywords()
        host_list.is_active_controller = MagicMock(return_value=True)
        order = []
        self.host_swact_mock.side_effect = lambda *a, **k: order.append("swact")
        self.wait_for_swact_mock.side_effect = lambda *a, **k: order.append("wait")

        with patcher:
            keywords.swact_if_active("controller-0")

        self.assertEqual(order, ["swact", "wait"])

    def test_swact_is_skipped_when_no_standby_exists(self):
        """On a single-controller system the swact is skipped rather than failing."""
        keywords, host_list, patcher = self._build_keywords(standby=None)
        host_list.is_active_controller = MagicMock(return_value=True)

        with patcher:
            performed = keywords.swact_if_active("controller-0")

        self.assertFalse(performed)
        self.host_swact_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
