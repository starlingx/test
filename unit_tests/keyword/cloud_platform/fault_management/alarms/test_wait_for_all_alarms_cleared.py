"""Unit tests for AlarmListKeywords alarm-clear debounce logic.

These tests exercise the dwell/consecutive-clear debounce shared by
wait_for_all_alarms_cleared (which delegates) and its unified core
wait_for_all_alarms_cleared_excluding. The alarm query is scripted per test to
simulate a flapping alarm. The wait reuses validate_equals_with_retry() for the
poll loop, so a shared virtual clock is patched into both that module and the
alarm keyword module; time.sleep advances the virtual clock instead of blocking,
so the dwell-window math runs deterministically and fast.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

import framework.validation.validation as validation_module
import keywords.base_keyword as base_keyword_module
import keywords.cloud_platform.fault_management.alarms.alarm_list_keywords as alarm_module
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject

# The framework logger refuses to run without a Logger Configuration. These unit
# tests exercise the real keyword classes (including the BaseKeyword logging hook),
# so get_logger is patched in every module that imported it by name, for the whole
# test module, to avoid requiring a Logger Configuration or writing a log tree.
_MOCK_LOGGER = MagicMock()
for _module in (alarm_module, validation_module, base_keyword_module):
    patch.object(_module, "get_logger", return_value=_MOCK_LOGGER).start()


def _make_alarm(alarm_id: str, entity_id: str = "host=controller-0", severity: str = "major") -> AlarmListObject:
    """Build an AlarmListObject with the given identity.

    Args:
        alarm_id (str): The alarm ID (e.g. "260.001").
        entity_id (str): The entity instance ID. Defaults to "host=controller-0".
        severity (str): The alarm severity. Defaults to "major".

    Returns:
        AlarmListObject: The constructed alarm object.
    """
    alarm = AlarmListObject()
    alarm.set_alarm_id(alarm_id)
    alarm.set_entity_id(entity_id)
    alarm.set_severity(severity)
    return alarm


class FakeClock:
    """Deterministic replacement for time.time()/sleep().

    sleep() advances a virtual clock instead of blocking, so timeout and dwell
    arithmetic based on time.time() progresses exactly by the slept amount.
    """

    def __init__(self):
        self._now = 1000.0

    def time(self) -> float:
        """Return the current virtual time.

        Returns:
            float: The virtual clock value in seconds.
        """
        return self._now

    def sleep(self, seconds: float) -> None:
        """Advance the virtual clock by the given number of seconds.

        Args:
            seconds (float): Seconds to advance the virtual clock.
        """
        self._now += seconds


@contextmanager
def _patched_clock_and_logger():
    """Patch the shared virtual clock and silence the logger for both modules.

    Yields:
        FakeClock: The shared virtual clock driving both the alarm keyword and
            the validation retry loop.
    """
    clock = FakeClock()
    # Drive both the alarm keyword's dwell math and the validation retry loop from
    # one virtual clock. sleep advances the clock instead of blocking.
    with patch.object(alarm_module.time, "time", clock.time), patch.object(validation_module.time, "time", clock.time), patch.object(validation_module, "sleep", clock.sleep):
        yield clock


def _build_keywords_with_alarm_sequence(alarm_samples: list) -> AlarmListKeywords:
    """Create an AlarmListKeywords whose alarm_list() yields scripted samples.

    A poll counter is exposed as 'keywords.poll_count' so tests can assert how many
    times the alarm list was queried (BaseKeyword wraps callables, so the MagicMock's
    own call_count is not reachable through normal attribute access).

    Args:
        alarm_samples (list): Ordered list of alarm-list results. Each element is a
            list of AlarmListObject returned on successive polls. The final element
            is repeated once the sequence is exhausted.

    Returns:
        AlarmListKeywords: Keyword instance with a mocked alarm_list().
    """
    keywords = AlarmListKeywords(MagicMock())

    samples = list(alarm_samples)
    poll_counter = {"count": 0}

    def _next_sample(*_args, **_kwargs) -> list:
        poll_counter["count"] += 1
        return samples.pop(0) if len(samples) > 1 else samples[0]

    keywords.alarm_list = MagicMock(side_effect=_next_sample)
    keywords.poll_counter = poll_counter
    return keywords


class TestWaitForAllAlarmsClearedDebounce:
    """Tests for the dwell/consecutive-clear debounce."""

    def test_flapping_alarm_only_returns_after_stable_dwell(self):
        """A clear sample followed by a reappearing alarm must not satisfy the dwell.

        Simulates: clear once, alarm reappears, then clears and stays clear. The
        method must keep waiting through the reappearance and only return after
        the alarm stays clear for the full dwell window.
        """
        alarm = _make_alarm("260.001")
        # Poll 1: clear. Poll 2: alarm back. Polls 3+: clear and stays clear.
        samples = [[], [alarm], []]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)

        with _patched_clock_and_logger() as clock:
            start = clock.time()
            keywords.wait_for_all_alarms_cleared(dwell_seconds=60, required_consecutive_clears=20)
            elapsed = clock.time() - start

        # The single early clear (poll 1) is invalidated by the reappearance (poll 2).
        # Success can only come after the alarm stays clear for the full 60s dwell.
        assert elapsed >= 60

    def test_returns_when_clear_and_stable(self):
        """Alarms clear from the start must satisfy the dwell after the window elapses."""
        samples = [[]]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)

        with _patched_clock_and_logger() as clock:
            start = clock.time()
            keywords.wait_for_all_alarms_cleared(dwell_seconds=60, required_consecutive_clears=20)
            elapsed = clock.time() - start

        # Must not return on the first empty sample; the dwell window must elapse.
        assert elapsed >= 60

    def test_single_empty_sample_does_not_pass_immediately(self):
        """A single empty sample must not be treated as steady state."""
        samples = [[]]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)

        with _patched_clock_and_logger():
            keywords.wait_for_all_alarms_cleared(dwell_seconds=60, required_consecutive_clears=20)

        # More than one poll is required to satisfy the dwell (20 consecutive clears).
        assert keywords.poll_counter["count"] >= 20

    def test_persistent_alarm_times_out(self):
        """An alarm that never clears must raise TimeoutError."""
        alarm = _make_alarm("260.001")
        samples = [[alarm]]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)
        keywords.set_timeout_in_seconds(30)

        with _patched_clock_and_logger():
            with pytest.raises(TimeoutError):
                keywords.wait_for_all_alarms_cleared(dwell_seconds=60, required_consecutive_clears=20)

    def test_transient_allowlist_alarm_does_not_block(self):
        """An alarm in the transient allowlist must not block or reset the dwell."""
        transient = _make_alarm("260.001")
        # 260.001 is always present but is treated as transient/still-reconciling.
        samples = [[transient]]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)

        with _patched_clock_and_logger() as clock:
            start = clock.time()
            keywords.wait_for_all_alarms_cleared(dwell_seconds=60, required_consecutive_clears=20, transient_alarm_ids=["260.001"])
            elapsed = clock.time() - start

        # Treated as clear the whole time -> returns once the dwell window elapses.
        assert elapsed >= 60

    def test_default_consecutive_clears_derived_from_interval(self):
        """When required_consecutive_clears is None it is derived from dwell/interval."""
        samples = [[]]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)

        with _patched_clock_and_logger():
            keywords.wait_for_all_alarms_cleared(dwell_seconds=60)

        # 60s dwell / 3s interval => ~20 consecutive clear polls required.
        assert keywords.poll_counter["count"] >= 20


class TestWaitForAllAlarmsClearedExcluding:
    """Tests for the unified wait_for_all_alarms_cleared_excluding core."""

    def test_count_only_returns_on_first_clear_by_default(self):
        """Default (stable_checks=1, dwell_seconds=0) returns on the first clear sample.

        Preserves the original count-only behavior for existing callers.
        """
        samples = [[]]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)

        with _patched_clock_and_logger() as clock:
            start = clock.time()
            keywords.wait_for_all_alarms_cleared_excluding()
            elapsed = clock.time() - start

        # First clear sample is enough: no dwell, one stable check.
        assert keywords.poll_counter["count"] == 1
        assert elapsed == 0

    def test_excluded_alarm_id_does_not_block(self):
        """An alarm whose ID is excluded must not block returning."""
        excluded = _make_alarm("900.007")
        samples = [[excluded]]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)

        with _patched_clock_and_logger():
            keywords.wait_for_all_alarms_cleared_excluding(excluded_alarm_ids=["900.007"])

        assert keywords.poll_counter["count"] == 1

    def test_stable_checks_requires_consecutive_clears(self):
        """stable_checks>1 must require that many consecutive clear polls."""
        samples = [[]]
        keywords = _build_keywords_with_alarm_sequence(samples)
        keywords.set_check_interval_in_seconds(3)

        with _patched_clock_and_logger():
            keywords.wait_for_all_alarms_cleared_excluding(stable_checks=3)

        assert keywords.poll_counter["count"] >= 3

    def test_tolerate_query_failure_keeps_polling(self):
        """A transient query failure must be retried when tolerate_query_failure is True."""
        keywords = AlarmListKeywords(MagicMock())
        keywords.set_check_interval_in_seconds(3)

        # Poll 1 raises (platform recovering), polls 2+ return clear.
        call_state = {"count": 0}

        def _alarm_list_side_effect(*_args, **_kwargs) -> list:
            call_state["count"] += 1
            if call_state["count"] == 1:
                raise RuntimeError("keystone unavailable")
            return []

        keywords.alarm_list = MagicMock(side_effect=_alarm_list_side_effect)

        with _patched_clock_and_logger():
            keywords.wait_for_all_alarms_cleared_excluding(tolerate_query_failure=True)

        # The first failed query did not abort the wait; it kept polling and succeeded.
        assert call_state["count"] >= 2

    def test_query_failure_propagates_by_default(self):
        """A query failure must propagate when tolerate_query_failure is False."""
        keywords = AlarmListKeywords(MagicMock())
        keywords.set_check_interval_in_seconds(3)
        keywords.alarm_list = MagicMock(side_effect=RuntimeError("keystone unavailable"))

        with _patched_clock_and_logger():
            with pytest.raises(RuntimeError, match="keystone unavailable"):
                keywords.wait_for_all_alarms_cleared_excluding()
