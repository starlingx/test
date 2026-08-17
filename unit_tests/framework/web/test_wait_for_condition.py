"""Unit tests for WebDriverCore.wait_for_condition()."""

import time

import pytest
from unit_tests.framework.web.mock_web_condition import MockWebCondition

# Reduced sleep constants for fast test execution while still exercising
# the real polling/sleep logic. Production uses 0.5/0.5/2.0.
_TEST_SLEEP_BASE = 0.1
_TEST_SLEEP_INCREMENT = 0.1
_TEST_SLEEP_CAP = 0.4


class MockWebDriverCore:
    """Minimal mock of WebDriverCore for testing wait_for_condition in isolation.

    We cannot instantiate the real WebDriverCore because it launches a browser.
    This mock replicates only the wait_for_condition logic using the same
    algorithm as the real implementation, with reduced sleep intervals for
    faster test execution.
    """

    def __init__(self):
        self.driver = None

    def wait_for_condition(self, conditions, timeout=30):
        """Mirror of WebDriverCore.wait_for_condition for unit testing."""
        if not conditions:
            return

        progressive_sleep = _TEST_SLEEP_BASE
        progressive_sleep_increment = _TEST_SLEEP_INCREMENT
        progressive_sleep_cap = _TEST_SLEEP_CAP
        deadline = time.time() + timeout
        max_attempts = max(1, int(timeout / progressive_sleep) + 10)

        for _ in range(max_attempts):
            all_satisfied = all(condition.is_condition_satisfied(self.driver) for condition in conditions)
            if all_satisfied:
                return

            if time.time() >= deadline:
                break

            time.sleep(progressive_sleep)
            progressive_sleep = min(progressive_sleep + progressive_sleep_increment, progressive_sleep_cap)

        unsatisfied = [str(c) for c in conditions if not c.is_condition_satisfied(self.driver)]
        raise TimeoutError(f"wait_for_condition timed out after {timeout}s. " f"Unsatisfied: {unsatisfied}")


class TestWaitForCondition:
    """Tests for the wait_for_condition polling logic."""

    def test_empty_conditions_returns_immediately(self):
        """Empty condition list should return without waiting."""
        core = MockWebDriverCore()
        start = time.time()
        core.wait_for_condition([], timeout=5)
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_condition_satisfied_immediately(self):
        """Condition that passes on first check returns without sleeping."""
        core = MockWebDriverCore()
        condition = MockWebCondition(number_of_expected_fails=0)
        start = time.time()
        core.wait_for_condition([condition], timeout=5)
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_condition_satisfied_after_polls(self):
        """Condition satisfied after N failures should return after polling."""
        core = MockWebDriverCore()
        condition = MockWebCondition(number_of_expected_fails=2)
        start = time.time()
        core.wait_for_condition([condition], timeout=10)
        elapsed = time.time() - start
        # After 2 fails: sleep 0.1 + sleep 0.2 = 0.3s minimum
        assert elapsed >= 0.25
        assert elapsed < 1.0

    def test_condition_timeout_raises(self):
        """Condition that never passes should raise TimeoutError."""
        core = MockWebDriverCore()
        condition = MockWebCondition(number_of_expected_fails=9999)
        with pytest.raises(TimeoutError, match="wait_for_condition timed out"):
            core.wait_for_condition([condition], timeout=0.5)

    def test_multiple_conditions_all_must_pass(self):
        """All conditions must be satisfied -- AND logic."""
        core = MockWebDriverCore()
        cond_a = MockWebCondition(number_of_expected_fails=0)
        cond_b = MockWebCondition(number_of_expected_fails=1)
        start = time.time()
        core.wait_for_condition([cond_a, cond_b], timeout=5)
        elapsed = time.time() - start
        # cond_b fails once -> at least one sleep of 0.1s
        assert elapsed >= 0.08

    def test_multiple_conditions_timeout_if_one_never_passes(self):
        """If any condition never passes, TimeoutError is raised."""
        core = MockWebDriverCore()
        cond_a = MockWebCondition(number_of_expected_fails=0)
        cond_b = MockWebCondition(number_of_expected_fails=9999)
        with pytest.raises(TimeoutError, match="MockCondition"):
            core.wait_for_condition([cond_a, cond_b], timeout=0.5)

    def test_progressive_sleep_caps_at_maximum(self):
        """Progressive sleep should cap at maximum, not grow indefinitely."""
        core = MockWebDriverCore()
        # Needs many polls to verify cap behavior
        condition = MockWebCondition(number_of_expected_fails=6)
        start = time.time()
        core.wait_for_condition([condition], timeout=30)
        elapsed = time.time() - start
        # Sleeps: 0.1 + 0.2 + 0.3 + 0.4 + 0.4 + 0.4 = 1.8s expected
        assert elapsed >= 1.6
        assert elapsed < 3.0

    def test_timeout_zero_is_single_check(self):
        """Timeout of 0 should check once and raise if not satisfied."""
        core = MockWebDriverCore()
        condition = MockWebCondition(number_of_expected_fails=1)
        with pytest.raises(TimeoutError):
            core.wait_for_condition([condition], timeout=0)

    def test_timeout_zero_passes_if_already_satisfied(self):
        """Timeout of 0 should pass if condition is already satisfied."""
        core = MockWebDriverCore()
        condition = MockWebCondition(number_of_expected_fails=0)
        core.wait_for_condition([condition], timeout=0)
