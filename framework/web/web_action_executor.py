import time
from typing import List

from framework.logging.automation_logger import get_logger
from framework.threading.thread_manager import ThreadManager
from framework.web.action.web_action import WebAction
from framework.web.web_locator import WebLocator
from selenium.webdriver.remote.webelement import WebElement


class WebActionExecutor:
    """
    This class executes WebDriver actions in a retry structure that makes use of stability conditions.
    """

    def __init__(self, web_action: WebAction):
        """
        Constructor which will instantiate the driver object.
        Args:
            web_action: Action that we want to perform.

        """

        self.web_action = web_action
        self.progressive_sleep = 1
        self.progressive_sleep_increment = 1

    def _find_element(self, locator: WebLocator) -> WebElement:
        """
        This function will attempt to find this element in the DOM.
        Args:
            locator: Element that we are trying to find in the DOM.

        Returns: A Selenium WebElement.
        """

        webdriver = self.web_action.get_webdriver()
        web_element = webdriver.find_element(locator.get_by(), locator.get_locator())
        return web_element

    def _find_all_elements(self, locator: WebLocator) -> List[WebElement]:
        """
        This function will attempt to find all the elements in the DOM matching the locator.
        Args:
            locator: Locator matching the elements that we want to find.

        Returns: A list of Selenium WebElement.
        """

        webdriver = self.web_action.get_webdriver()
        web_elements = webdriver.find_elements(locator.get_by(), locator.get_locator())
        return web_elements

    def _is_a_condition_satisfied(self):
        """
        This function will check if a condition is satisfied.
        Returns:
            True if there is no condition associated with the action.
            True if at least one condition associated with the action is satisfied.
            False otherwise.
        """

        is_a_condition_satisfied = False

        # Assume that the action was a success if there is no condition.
        if len(self.web_action.get_conditions()) == 0:
            get_logger().log_debug("No Condition Found - Validation is Successful")
            is_a_condition_satisfied = True

            # Check if at least one condition is satisfied.
        for condition in self.web_action.get_conditions():
            get_logger().log_debug(f"Checking Condition - {condition}")
            if condition.is_condition_satisfied(self.web_action.get_webdriver()):
                is_a_condition_satisfied = True
                get_logger().log_debug(f"Condition Satisfied! - {condition}")
                break

        return is_a_condition_satisfied

    def _execute_action(self, *args):
        """
        This function will execute the action with the arguments specified
        Args:
            *args: Parameters to pass in to the action function.

        Returns:
            The output of the action if it is successful.

        """

        state = "NOT_FOUND"
        is_action_done = False
        value = None

        timeout = time.time() + self.web_action.get_timeout()
        while state != "COMPLETE" and time.time() < timeout:

            try:

                if state == "NOT_FOUND":

                    # Find the element.
                    web_locator = self.web_action.get_web_locator()
                    web_element = self._find_element(web_locator)
                    get_logger().log_debug(f"Found Element - {self.web_action.get_web_locator()}")
                    state = "FOUND"

                if state == "FOUND":

                    # Execute the Specified Action
                    get_logger().log_debug(f"Attempting to perform {self.web_action} on - {self.web_action.get_web_locator()}")
                    value = self.web_action.perform_action(web_element, *args)
                    is_action_done = True
                    state = "VALIDATING"

                if state == "VALIDATING":

                    if self._is_a_condition_satisfied():
                        state = "COMPLETE"
                    else:
                        get_logger().log_debug("Failed to satisfy a condition, moving to UNKNOWN state")
                        state = "UNKNOWN"

                if state == "UNKNOWN":

                    get_logger().log_debug(f"Sleep for {self.progressive_sleep}s")
                    time.sleep(self.progressive_sleep)
                    self.progressive_sleep += self.progressive_sleep_increment

                    if is_action_done and self._is_a_condition_satisfied():
                        state = "COMPLETE"
                    else:
                        # Try the action again.
                        if is_action_done:
                            get_logger().log_debug("Failed to satisfy the conditions again, moving to NOT_FOUND state")
                        state = "NOT_FOUND"

            except Exception as e:
                get_logger().log_debug(e)
                get_logger().log_debug("Exception occurred during action, moving to UNKNOWN state")
                state = "UNKNOWN"

        if state != "COMPLETE":
            raise Exception(f"Failed to perform Action {self.web_action}")

        return value

    def execute_action(self, *args):
        """
        This function will execute the action with the arguments specified
        This is the threaded version that calls _execute_action.

        Args:
            *args: Parameters to pass in to the action function.

        Returns:
            The output of the action if it is successful.

        """
        # Thread the Selenium operation to ensure that we maintain control if it hangs.
        thread_manager_send = ThreadManager(timeout=1.5 * self.web_action.get_timeout())
        thread_manager_send.start_thread("Selenium", self._execute_action, *args)
        thread_manager_send.join_all_threads()
        value = thread_manager_send.get_thread_object("Selenium").get_result()
        return value

    def _execute_mass_action(self, *args):
        """
        This function will execute the action specified on all the WebElements that match the WebLocator.
        Args:
            *args: Parameters to pass in to the action function.

        Returns:
            A List of the outputs of the actions.

        """

        state = "NOT_FOUND"
        is_action_done = False
        values = []

        timeout = time.time() + self.web_action.get_timeout()
        while state != "COMPLETE" and time.time() < timeout:

            try:

                if state == "NOT_FOUND":

                    # Find the element.
                    web_locator = self.web_action.get_web_locator()
                    web_elements = self._find_all_elements(web_locator)
                    get_logger().log_debug(f"Found {len(web_elements)} Elements Matching - {self.web_action.get_web_locator()}")
                    state = "FOUND"

                if state == "FOUND":

                    # Execute the Specified Action
                    values = []
                    get_logger().log_debug(f"Attempting to perform {self.web_action} on every element matching - {self.web_action.get_web_locator()}")
                    for element in web_elements:
                        value = self.web_action.perform_action(element, *args)
                        values.append(value)

                    is_action_done = True
                    state = "VALIDATING"

                if state == "VALIDATING":

                    if self._is_a_condition_satisfied():
                        state = "COMPLETE"
                    else:
                        get_logger().log_debug("Failed to satisfy a condition, moving to UNKNOWN state")
                        state = "UNKNOWN"

                if state == "UNKNOWN":

                    get_logger().log_debug(f"Sleep for {self.progressive_sleep}s")
                    time.sleep(self.progressive_sleep)
                    self.progressive_sleep += self.progressive_sleep_increment

                    if is_action_done and self._is_a_condition_satisfied():
                        state = "COMPLETE"
                    else:
                        # Try the action again.
                        if is_action_done:
                            get_logger().log_debug("Failed to satisfy the conditions again, moving to NOT_FOUND state")
                        state = "NOT_FOUND"

            except Exception as e:
                get_logger().log_debug(e)
                get_logger().log_debug("Exception occurred during action, moving to UNKNOWN state")
                state = "UNKNOWN"

        if state != "COMPLETE":
            raise Exception(f"Failed to perform Mass Action {self.web_action}")

        return values

    def execute_mass_action(self, *args):
        """
        This function will execute the action specified on all the WebElements that match the WebLocator.
        This is the threaded version that calls _execute_mass_action.

        Args:
            *args: Parameters to pass in to the action function.

        Returns:
            A List of the outputs of the actions.

        """
        # Thread the Selenium operation to ensure that we maintain control if it hangs.
        thread_manager_send = ThreadManager(timeout=1.5 * self.web_action.get_timeout())
        thread_manager_send.start_thread("Selenium", self._execute_mass_action, *args)
        thread_manager_send.join_all_threads()
        values = thread_manager_send.get_thread_object("Selenium").get_result()
        return values
