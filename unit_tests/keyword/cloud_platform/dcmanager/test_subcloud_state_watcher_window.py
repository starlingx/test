"""Unit tests for DcManagerSubcloudStateWatcherKeywords.watch_strategy_steps_for_window."""

from unittest.mock import MagicMock, NonCallableMagicMock, patch

import pytest

from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import DcManagerSubcloudStateWatcherKeywords

WATCHER_MODULE = "keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords"


@pytest.fixture(autouse=True)
def silence_loggers():
    """Patch the loggers used by the watcher, which raise without a logger config.

    Yields:
        None: Control returns to the test with the loggers patched.
    """
    with patch(f"{WATCHER_MODULE}.get_logger"), patch("keywords.base_keyword.get_logger"), patch(f"{WATCHER_MODULE}.time.sleep"):
        yield


def build_watcher(step_states_sequence: list, details: str = "") -> DcManagerSubcloudStateWatcherKeywords:
    """Build a watcher whose strategy-step polling returns the given states in order.

    Args:
        step_states_sequence (list): One dict of {subcloud: state} per poll.
        details (str): Strategy-step details reported for a failed step.

    Returns:
        DcManagerSubcloudStateWatcherKeywords: Watcher with polling stubbed out.
    """
    watcher = DcManagerSubcloudStateWatcherKeywords(MagicMock())
    watcher._get_strategy_step_states = MagicMock(side_effect=step_states_sequence)
    # NonCallable: BaseKeyword wraps callable attributes, hiding their methods.
    step_kw = NonCallableMagicMock()
    step_kw.get_dcmanager_strategy_step_show.return_value.get_dcmanager_strategy_step_show.return_value.get_details.return_value = details
    watcher._strategy_step_kw = step_kw
    return watcher


def test_window_watch_returns_last_states_when_no_failure():
    """A watch that sees no failed state returns the last observed states."""
    watcher = build_watcher([{"subcloud1": "applying"}])

    last_states = watcher.watch_strategy_steps_for_window(subcloud_names=["subcloud1"], window=0, polling_interval=0)

    assert last_states == {"subcloud1": "applying"}


def test_window_watch_raises_on_failure_when_not_expected():
    """A failed state raises and surfaces the step details when expect_failure is False."""
    watcher = build_watcher([{"subcloud1": "failed"}], details="build rejected")

    with pytest.raises(Exception, match="build rejected"):
        watcher.watch_strategy_steps_for_window(subcloud_names=["subcloud1"], window=0, polling_interval=0)


def test_window_watch_returns_on_failure_when_expected():
    """A failed state ends the watch successfully when expect_failure is True."""
    watcher = build_watcher([{"subcloud1": "failed"}])

    last_states = watcher.watch_strategy_steps_for_window(subcloud_names=["subcloud1"], window=0, expect_failure=True, polling_interval=0)

    assert last_states == {"subcloud1": "failed"}


def test_window_watch_raises_when_expected_failure_does_not_happen():
    """Surviving the window raises when a failure was expected."""
    watcher = build_watcher([{"subcloud1": "applying"}])

    with pytest.raises(Exception, match="No strategy step failed"):
        watcher.watch_strategy_steps_for_window(subcloud_names=["subcloud1"], window=0, expect_failure=True, polling_interval=0)


def test_window_watch_ignores_unwatched_subclouds():
    """States of subclouds outside the watched set are not reported or acted on."""
    watcher = build_watcher([{"subcloud1": "applying", "subcloud2": "failed"}])

    last_states = watcher.watch_strategy_steps_for_window(subcloud_names=["subcloud1"], window=0, polling_interval=0)

    assert last_states == {"subcloud1": "applying"}


def test_window_watch_rejects_empty_subcloud_list():
    """An empty subcloud list is rejected up front."""
    watcher = build_watcher([])

    with pytest.raises(ValueError, match="must not be empty"):
        watcher.watch_strategy_steps_for_window(subcloud_names=[], window=0)
