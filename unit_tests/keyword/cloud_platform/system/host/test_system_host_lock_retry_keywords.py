"""Unit tests for the SystemHostLockKeywords.lock_host opt-in retry.

lock_host keeps its single-attempt behaviour by default (retries=0): every existing caller issues
one 'system host-lock', asserts success, and waits for the locked state. Callers that run during a
platform deploy/rollback can opt in to retrying a transient server-side error by passing retries>0.
These tests pin both contracts: the default path is unchanged, and the opt-in path retries,
short-circuits on an already-locked host, does a final locked-check before giving up, and does not
sleep past the last attempt.
"""

import unittest
from unittest.mock import MagicMock, patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords

MODULE = "keywords.cloud_platform.system.host.system_host_lock_keywords"


class LockHostRetryTests(unittest.TestCase):
    """Contracts for lock_host's default single attempt and its opt-in retry."""

    def setUp(self):
        """Silence the BaseKeyword keyword-logging wrapper, which needs a configured logger."""
        patcher = patch("keywords.base_keyword.get_logger")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _keywords(self):
        """Return a SystemHostLockKeywords with a stubbed ssh connection and _lock_host_once."""
        keywords = SystemHostLockKeywords.__new__(SystemHostLockKeywords)
        keywords.ssh_connection = MagicMock()
        return keywords

    def test_default_is_single_attempt_no_retry(self):
        """retries=0 (default) issues exactly one lock and never consults is_host_locked."""
        keywords = self._keywords()
        once = MagicMock(return_value=True)
        is_locked = MagicMock()
        with patch.object(keywords, "_lock_host_once", once), patch.object(keywords, "is_host_locked", is_locked):
            result = keywords.lock_host("controller-0")
        self.assertTrue(result)
        once.assert_called_once_with("controller-0")
        is_locked.assert_not_called()

    def test_default_propagates_the_error(self):
        """retries=0 lets a lock failure propagate unchanged (no swallow, no retry)."""
        keywords = self._keywords()
        with patch.object(keywords, "_lock_host_once", MagicMock(side_effect=KeywordException("did not lock"))):
            with self.assertRaises(KeywordException):
                keywords.lock_host("controller-0")

    def test_retry_succeeds_first_try_does_not_consult_is_host_locked(self):
        """With retries>0 but a clean first lock, is_host_locked is not consulted."""
        keywords = self._keywords()
        once = MagicMock(return_value=True)
        is_locked = MagicMock()
        with patch.object(keywords, "_lock_host_once", once), patch.object(keywords, "is_host_locked", is_locked), patch(f"{MODULE}.get_logger"):
            keywords.lock_host("controller-1", retries=2, retry_delay=0)
        once.assert_called_once_with("controller-1")
        is_locked.assert_not_called()

    def test_retry_transient_error_then_succeeds(self):
        """A transient error is retried and the next attempt succeeds."""
        keywords = self._keywords()
        once = MagicMock(side_effect=[Exception("'str' object has no attribute 'get'"), True])
        with patch.object(keywords, "_lock_host_once", once), patch.object(keywords, "is_host_locked", MagicMock(return_value=False)), patch(f"{MODULE}.get_logger"):
            keywords.lock_host("controller-1", retries=2, retry_delay=0)
        self.assertEqual(once.call_count, 2)

    def test_retry_returns_if_already_locked_after_error(self):
        """If a prior attempt actually locked the host despite the error, no second lock is issued."""
        keywords = self._keywords()
        once = MagicMock(side_effect=Exception("'str' object has no attribute 'get'"))
        with patch.object(keywords, "_lock_host_once", once), patch.object(keywords, "is_host_locked", MagicMock(return_value=True)), patch(f"{MODULE}.get_logger"):
            keywords.lock_host("controller-1", retries=2, retry_delay=0)
        self.assertEqual(once.call_count, 1)  # first attempt failed, then detected already locked

    def test_retry_final_check_catches_last_attempt_lock(self):
        """If the final attempt errored but the host is in fact locked, do not raise."""
        keywords = self._keywords()
        once = MagicMock(side_effect=Exception("did not lock in the required time"))
        # Not locked at the retry-guard check (before attempt 2), locked by the final post-loop check.
        is_locked = MagicMock(side_effect=[False, True])
        with patch.object(keywords, "_lock_host_once", once), patch.object(keywords, "is_host_locked", is_locked), patch(f"{MODULE}.get_logger"):
            keywords.lock_host("controller-1", retries=1, retry_delay=0)
        self.assertEqual(once.call_count, 2)

    def test_retry_raises_after_exhausting_attempts(self):
        """A persistent failure raises after all attempts, not hiding a real problem."""
        keywords = self._keywords()
        once = MagicMock(side_effect=Exception("boom"))
        with patch.object(keywords, "_lock_host_once", once), patch.object(keywords, "is_host_locked", MagicMock(return_value=False)), patch(f"{MODULE}.get_logger"):
            with self.assertRaises(KeywordException):
                keywords.lock_host("controller-1", retries=1, retry_delay=0)
        self.assertEqual(once.call_count, 2)  # retries=1 -> 2 attempts

    def test_retry_does_not_sleep_after_the_final_attempt(self):
        """A persistent failure raises without sleeping an extra retry_delay past the last attempt."""
        keywords = self._keywords()
        once = MagicMock(side_effect=Exception("boom"))
        with patch.object(keywords, "_lock_host_once", once), patch.object(keywords, "is_host_locked", MagicMock(return_value=False)), patch(f"{MODULE}.get_logger"), patch(f"{MODULE}.time.sleep") as sleep_mock:
            with self.assertRaises(KeywordException):
                keywords.lock_host("controller-1", retries=2, retry_delay=20)
        # retries=2 -> 3 attempts -> sleep only between them (after attempts 1 and 2), never last.
        self.assertEqual(sleep_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
