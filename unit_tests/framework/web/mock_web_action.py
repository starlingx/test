from typing import List

from framework.web.action.web_action import WebAction
from framework.web.condition.web_condition import WebCondition


class MockWebAction(WebAction):
    """
    Class Mocking a Web Action
    """

    def __init__(self, number_of_expected_fails: int = 0, web_conditions: List[WebCondition] = []):
        """
        Constructor which will instantiate the driver object.
        Args:
            number_of_expected_fails: Number of times to throw and exception when perform_action is called.
        """
        super().__init__(None, None, web_conditions=web_conditions)
        self.number_of_expected_fails = number_of_expected_fails
        self.timeout = 0.01  # For unit tests, 10ms is a long time in the loop.

    def perform_action(self, web_element, *args):
        """
        Override the parent's perform action with a mock action
        Args:
            web_element: Element.
            *args: Unused arguments to follow the override signature.

        Returns: Success as a string

        """
        if self.number_of_expected_fails > 0:
            self.number_of_expected_fails -= 1
            raise Exception("Failed to Perform Mock Action")

        return "Success"

    def __str__(self):
        """
        String representation of this action.
        Returns:

        """
        return "Mock Action"
