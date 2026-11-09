"""Web condition that checks the number of elements matching a locator."""

from framework.logging.automation_logger import get_logger
from framework.web.condition.web_condition import WebCondition
from framework.web.web_locator import WebLocator
from selenium.webdriver.remote.webdriver import WebDriver


class WebConditionElementCountEquals(WebCondition):
    """Web Condition satisfied when the number of elements matching the locator equals an expected count."""

    def __init__(self, web_locator: WebLocator, expected_count: int):
        """Initialize the condition.

        Args:
            web_locator (WebLocator): The locator of the elements to count.
            expected_count (int): The number of matching elements that satisfies the condition.
        """
        super().__init__(web_locator)
        self.expected_count = expected_count

    def get_expected_count(self) -> int:
        """Get the expected element count.

        Returns:
            int: The number of matching elements that satisfies the condition.
        """
        return self.expected_count

    def is_condition_satisfied(self, webdriver: WebDriver) -> bool:
        """Evaluate the condition and return True if it is satisfied, False otherwise.

        Args:
            webdriver (WebDriver): The Selenium webdriver instance.

        Returns:
            bool: True if the number of matching elements equals the expected count, False otherwise.
        """
        try:
            web_elements = webdriver.find_elements(self.get_web_locator().get_by(), self.get_web_locator().get_locator())
            return len(web_elements) == self.get_expected_count()
        except Exception:
            get_logger().log_debug("Exception occurred evaluating WebConditionElementCountEquals, returning false")
            return False

    def __str__(self) -> str:
        """Get a readable representation of this condition.

        Returns:
            str: Description including the locator and the expected count.
        """
        return f"ElementCountEquals - {self.get_web_locator()} expected {self.get_expected_count()}"
