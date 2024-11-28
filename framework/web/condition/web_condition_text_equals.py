from framework.logging.automation_logger import get_logger
from framework.web.condition.web_condition import WebCondition
from framework.web.web_locator import WebLocator


class WebConditionTextEquals(WebCondition):
    """
    This Web Condition will check if the Text Contents of the element is a expected.
    """

    def __init__(self, web_locator: WebLocator, expected_text: str):
        """
        Constructor which will instantiate the driver object.
        Args:
            web_locator: Locator for the WebElement of interest
            expected_text: The expected text content for the condition to be met.
        """

        self.web_locator = web_locator
        self.expected_text = expected_text

    def is_condition_satisfied(self, webdriver) -> bool:
        """
        This function will evaluate the web_condition and return True if the text of the element is as expected.

        Returns:

        """

        web_element = webdriver.find_element(self.get_web_locator().get_by(), self.get_web_locator().get_locator())
        web_element_actual_text = web_element.text
        if not web_element_actual_text:
            web_element_actual_text = web_element.get_attribute('value')

        get_logger().log_debug(f"Expected: '{self.expected_text}' | Actual: '{web_element_actual_text}'")

        return web_element_actual_text == self.expected_text

    def __str__(self):
        """
        Nice String representation for this condition.
        Returns:

        """
        return f"ElementTextEquals {self.expected_text} - {self.get_web_locator()}"
