from selenium.webdriver.remote.webdriver import WebDriver

from framework.logging.automation_logger import get_logger
from framework.web.condition.web_condition import WebCondition


class WebConditionElementVisible(WebCondition):
    """
    This Web Condition will check if the WebElement is Visible on the screen.
    """

    def is_condition_satisfied(self, webdriver: WebDriver) -> bool:
        """
        This function will evaluate the web_condition and return True if it is satisfied and False otherwise.

        Args:
            webdriver (WebDriver): The Selenium webdriver instance.

        Returns:
            bool: True if the element is visible, False otherwise.
        """
        try:
            web_element = webdriver.find_elements(self.get_web_locator().get_by(), self.get_web_locator().get_locator())
            is_element_found = len(web_element) > 0
        except Exception:
            get_logger().log_debug("Exception occurred evaluating WebConditionElementVisible, returning false")
            is_element_found = False

        return is_element_found

    def __str__(self):
        """
        Nice String representation for this condition.
        """
        return f"ElementVisible - {self.get_web_locator()}"
