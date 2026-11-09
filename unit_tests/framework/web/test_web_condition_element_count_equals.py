"""Unit tests for WebConditionElementCountEquals."""

from typing import NoReturn

from framework.web.condition import web_condition_element_count_equals as condition_module
from framework.web.condition.web_condition_element_count_equals import WebConditionElementCountEquals
from framework.web.web_locator import WebLocator
from pytest import MonkeyPatch


class FakeLogger:
    """Fake logger that discards debug messages."""

    def log_debug(self, message: str) -> None:
        """Discard the message.

        Args:
            message (str): Message to discard.
        """


class FakeWebDriver:
    """Fake webdriver whose find_elements returns a list of a desired length."""

    def __init__(self, element_count: int):
        """Initialize the fake webdriver.

        Args:
            element_count (int): Number of elements find_elements should return.
        """
        self.element_count = element_count
        self.calls = []

    def find_elements(self, by: str, locator: str) -> list:
        """Record the call and return a list of fake elements.

        Args:
            by (str): Locator strategy.
            locator (str): Locator value.

        Returns:
            list: List with element_count entries.
        """
        self.calls.append((by, locator))
        return [object() for _ in range(self.element_count)]


class RaisingWebDriver:
    """Fake webdriver whose find_elements always raises."""

    def find_elements(self, by: str, locator: str) -> NoReturn:
        """Raise an exception.

        Args:
            by (str): Locator strategy.
            locator (str): Locator value.

        Raises:
            RuntimeError: Always.
        """
        raise RuntimeError("find_elements failed")


class SequenceWebDriver:
    """Fake webdriver returning a different element count on each call."""

    def __init__(self, counts: list):
        """Initialize the fake webdriver.

        Args:
            counts (list): Element counts to return, in call order. The last one repeats.
        """
        self.counts = counts
        self.call_index = 0

    def find_elements(self, by: str, locator: str) -> list:
        """Return a list whose length follows the configured sequence.

        Args:
            by (str): Locator strategy.
            locator (str): Locator value.

        Returns:
            list: List of fake elements.
        """
        index = min(self.call_index, len(self.counts) - 1)
        self.call_index += 1
        return [object() for _ in range(self.counts[index])]


def build_locator() -> WebLocator:
    """Build a locator used across the tests.

    Returns:
        WebLocator: An XPath locator.
    """
    return WebLocator("//table//tr", "xpath")


class TestWebConditionElementCountEquals:
    """Tests for WebConditionElementCountEquals."""

    def test_count_matches_returns_true(self):
        """Condition is satisfied when the found count equals the expected count."""
        condition = WebConditionElementCountEquals(build_locator(), 3)
        assert condition.is_condition_satisfied(FakeWebDriver(3)) is True

    def test_fewer_elements_returns_false(self):
        """Condition is not satisfied when fewer elements are found."""
        condition = WebConditionElementCountEquals(build_locator(), 3)
        assert condition.is_condition_satisfied(FakeWebDriver(2)) is False

    def test_more_elements_returns_false(self):
        """Condition is not satisfied when more elements are found."""
        condition = WebConditionElementCountEquals(build_locator(), 3)
        assert condition.is_condition_satisfied(FakeWebDriver(4)) is False

    def test_zero_expected_with_no_elements_returns_true(self):
        """Condition is satisfied when zero is expected and nothing is found."""
        condition = WebConditionElementCountEquals(build_locator(), 0)
        assert condition.is_condition_satisfied(FakeWebDriver(0)) is True

    def test_no_elements_found_but_some_expected_returns_false(self):
        """Condition is not satisfied when nothing is found but elements are expected."""
        condition = WebConditionElementCountEquals(build_locator(), 2)
        assert condition.is_condition_satisfied(FakeWebDriver(0)) is False

    def test_find_elements_exception_returns_false(self, monkeypatch: MonkeyPatch) -> None:
        """An unknown count must not satisfy the condition, even when zero is expected.

        Args:
            monkeypatch (MonkeyPatch): Used to replace the logger, which is not configured in unit tests.
        """
        monkeypatch.setattr(condition_module, "get_logger", lambda: FakeLogger())
        condition = WebConditionElementCountEquals(build_locator(), 0)
        assert condition.is_condition_satisfied(RaisingWebDriver()) is False

    def test_get_expected_count(self):
        """The getter returns the expected count given to the constructor."""
        condition = WebConditionElementCountEquals(build_locator(), 7)
        assert condition.get_expected_count() == 7

    def test_str_contains_locator_and_count(self):
        """The string representation includes the locator and the expected count."""
        locator = build_locator()
        text = str(WebConditionElementCountEquals(locator, 5))
        assert str(locator) in text
        assert "expected 5" in text
        assert text.startswith("ElementCountEquals")

    def test_find_elements_called_with_locator_values(self):
        """find_elements is called with the locator's by and locator values."""
        locator = build_locator()
        driver = FakeWebDriver(1)
        WebConditionElementCountEquals(locator, 1).is_condition_satisfied(driver)
        assert driver.calls == [(locator.get_by(), locator.get_locator())]

    def test_get_web_locator_returns_locator(self):
        """The base class getter returns the locator given to the constructor."""
        locator = build_locator()
        assert WebConditionElementCountEquals(locator, 1).get_web_locator() is locator

    def test_polling_loop_with_changing_counts(self):
        """Condition becomes satisfied once the count settles on the expected value."""
        condition = WebConditionElementCountEquals(build_locator(), 2)
        driver = SequenceWebDriver([5, 4, 2])

        results = [condition.is_condition_satisfied(driver) for _ in range(3)]

        assert results == [False, False, True]
