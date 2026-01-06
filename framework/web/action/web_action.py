from abc import abstractmethod
from typing import List

from selenium.webdriver import ActionChains

from framework.web.condition.web_condition import WebCondition
from framework.web.web_locator import WebLocator


class WebAction:
    """
    This is an abstract class that implements actions that will be performed by the action executor.
    """

    def __init__(self, webdriver, web_locator: WebLocator, web_conditions: List[WebCondition] = []):
        """
        Constructor which will instantiate the driver object.
        Args:
            webdriver: Instance of the Selenium WebDriver object to use.
            web_locator: Locator of the element that we want to act on.
            web_conditions: Conditions that should be satisfied if the action is successful.
        """

        self.webdriver = webdriver
        self.web_locator = web_locator
        self.web_conditions = web_conditions
        self.actions = ActionChains(self.webdriver)
        self.timeout = 30

    def get_webdriver(self):
        """
        Getter for the Webdriver
        Returns:

        """

        return self.webdriver

    def get_web_locator(self) -> WebLocator:
        """
        Getter for the Web locator
        Returns:

        """
        return self.web_locator

    def get_conditions(self) -> List[WebCondition]:
        """
        This function will return the list of conditions associated with this action.
        Returns:

        """
        return self.web_conditions

    def get_timeout(self) -> int:
        """
        This function will return the timeout associated with this action.
        Returns:

        """
        return self.timeout

    @abstractmethod
    def perform_action(self, web_element, *args):
        """
        Abstract Function
        This function contains the details of the action to perform.
        Args:
            web_element: Selenium WebElement
            *args: Arguments that we want to pass to this function.

        Returns:

        """
        pass

    @abstractmethod
    def __str__(self):
        """
        Forcing child classes to have a nice String representation for the logger.
        Returns:

        """
        return "Action"
