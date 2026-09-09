from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from framework.logging.automation_logger import get_logger
from framework.web.condition.web_condition import WebCondition


class WebConditionNewWindowOpened(WebCondition):
    """
    This Web Condition will check if a new browser window/tab has opened since the condition was created.

    It compares the current number of window handles against the baseline count captured before the
    triggering action (e.g. a click that calls window.open). It is not tied to a WebLocator.
    """

    def __init__(self, initial_window_count: int):
        """
        Constructor.

        Args:
            initial_window_count (int): The number of window handles before the triggering action.
        """
        super().__init__(web_locator=None)
        self.initial_window_count = initial_window_count

    def is_condition_satisfied(self, webdriver: WebDriver) -> bool:
        """
        This function will evaluate the web_condition and return True if it is satisfied and False otherwise.

        Args:
            webdriver (WebDriver): The Selenium webdriver instance.

        Returns:
            bool: True if a new window/tab has opened (handle count increased), False otherwise.
        """
        try:
            is_new_window_opened = len(webdriver.window_handles) > self.initial_window_count
        except WebDriverException:
            get_logger().log_debug("WebDriverException occurred evaluating WebConditionNewWindowOpened, returning false")
            is_new_window_opened = False

        return is_new_window_opened

    def __str__(self) -> str:
        """
        Nice String representation for this condition.

        Returns:
            str: A human-readable description of this condition.
        """
        return f"NewWindowOpened - baseline window count {self.initial_window_count}"
