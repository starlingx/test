import time
from typing import List

import selenium
from selenium import webdriver

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.web.action.web_action_click import WebActionClick
from framework.web.action.web_action_get_text import WebActionGetText
from framework.web.action.web_action_set_text import WebActionSetText
from framework.web.condition.web_condition import WebCondition
from framework.web.condition.web_condition_text_equals import WebConditionTextEquals
from framework.web.web_action_executor import WebActionExecutor
from framework.web.web_locator import WebLocator


class WebDriverCore:
    """
    This class is a wrapper around the Web Driver object used to perform operations on a Web Page.
    """

    def __init__(self):
        """
        Constructor which will instantiate the driver object.
        """

        chrome_options = selenium.webdriver.chrome.options.Options()
        chrome_options.add_argument("--ignore-certificate-errors")
        if ConfigurationManager.get_web_config().get_run_headless():
            chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)

    def close(self) -> None:
        """
        Close the WebDriver and browser window.
        Returns: None

        """
        self.driver.close()

    def navigate_to_url(self, url: str, conditions: List[WebCondition] = []) -> None:
        """
        This function will navigate to the specified url.
        The navigation will get retried if until one of the conditions is met (or we time out).

        Args:
            url: URL to navigate to.
            conditions: Conditions for successful navigation to this URL.

        Returns: None

        """
        self.driver.get(url)

        is_navigation_success = False
        if len(conditions) == 0:
            is_navigation_success = True

        timeout = time.time() + 30
        reload_attempt_timeout = 2
        while not is_navigation_success and time.time() < timeout:

            for condition in conditions:
                if condition.is_condition_satisfied(self.driver):
                    get_logger().log_debug(f"Condition Satisfied: {condition}")
                    is_navigation_success = True

            if not is_navigation_success:
                get_logger().log_debug(f"Failed to load page with URL: {url}")
                get_logger().log_debug(f"Reload page and sleep for {reload_attempt_timeout} seconds ")
                self.driver.get(url)
                time.sleep(reload_attempt_timeout)
                reload_attempt_timeout += 2

        if is_navigation_success:
            get_logger().log_debug(f"Navigation to {url} successful.")
        else:
            raise Exception(f"Page {url} failed to load after 30 seconds.")

    def click(self, locator: WebLocator, conditions: List[WebCondition] = []) -> None:
        """
        Click on the target element
        Args:
            locator: The locator of the element that we want to click on.
            conditions: Conditions that must be satisfied for the Action to be declared successful.

        Returns: None

        """

        action = WebActionClick(self.driver, locator, conditions)
        action_executor = WebActionExecutor(action)
        action_executor.execute_action()

    def set_text(self, locator: WebLocator, text: str, conditions: List[WebCondition] = []) -> None:
        """
        Clears the text content of the element, then sets the text of the element.
        Args:
            locator: The locator of the element that we want to set the text of.
            text: The text that we want to set.
            conditions: Conditions that must be satisfied for the Action to be declared successful.

        Returns: None

        """

        conditions_clone = [condition for condition in conditions]
        conditions_clone.append(WebConditionTextEquals(locator, text))
        action = WebActionSetText(self.driver, locator, conditions_clone)
        action_executor = WebActionExecutor(action)
        action_executor.execute_action(text)

    def get_text(self, locator: WebLocator, conditions: List[WebCondition] = []) -> str:
        """
        Gets the Text content of the element
        Args:
            locator: The locator of the element from which we want to get the text contents.
            conditions: Conditions that must be satisfied for the Action to be declared successful.

        Returns: None

        """

        action = WebActionGetText(self.driver, locator, conditions)
        action_executor = WebActionExecutor(action)
        return action_executor.execute_action()

    def get_all_elements_text(self, locator: WebLocator, conditions: List[WebCondition] = []) -> List[str]:
        """
        Gets the text content of all the elements that are matching the locator.
        Args:
            locator: A locator that matches multiple elements from which we want to get the text.
            conditions: Conditions that must be satisfied for the Action to be declared successful.

        Returns: None

        """

        action = WebActionGetText(self.driver, locator, conditions)
        action_executor = WebActionExecutor(action)
        return action_executor.execute_mass_action()
