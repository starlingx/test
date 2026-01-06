from selenium import webdriver

from framework.logging.automation_logger import get_logger
from framework.web.condition.web_condition import WebCondition
from framework.web.web_locator import WebLocator


class WebConditionAttributeEquals(WebCondition):
    """
    This Web Condition will check if the Attribute of the element has the expected value.
    """

    def __init__(self, web_locator: WebLocator, attribute_name: str, expected_value: str):
        """
        Constructor which will instantiate the driver object.

        Args:
            web_locator (WebLocator): Locator for the WebElement of interest
            attribute_name (str): Name of the attribute to expect.
            expected_value (str): The expected value of the attribute.
        """
        self.web_locator = web_locator
        self.attribute_name = attribute_name
        self.expected_value = expected_value

    def is_condition_satisfied(self, webdriver: webdriver) -> bool:
        """
        This function will evaluate the web_condition and return True if the text of the element is as expected.

        Args:
            webdriver (webdriver): The Selenium webdriver instance

        Returns:
            bool: True if the value of the attribute matches the expected_value

        """
        web_element = webdriver.find_element(self.get_web_locator().get_by(), self.get_web_locator().get_locator())
        web_element_actual_attribute_value = web_element.get_attribute(self.attribute_name)

        get_logger().log_debug(f"Attribute {self.attribute_name} Expected: '{self.expected_value}' | Actual: '{web_element_actual_attribute_value}'")

        return web_element_actual_attribute_value == self.expected_value

    def __str__(self) -> str:
        """
        Nice String representation for this condition.

        Returns:
            str:

        """
        return f"ElementAttributeEquals {self.attribute_name} = {self.expected_value} - {self.get_web_locator()}"
