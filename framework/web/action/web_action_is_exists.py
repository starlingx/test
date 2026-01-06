from selenium.webdriver.remote.webelement import WebElement

from framework.web.action.web_action import WebAction


class WebActionIsExists(WebAction):
    """
    Class representing a Web Is Exists action.
    """

    def perform_action(self, web_element: WebElement, *args):
        """
        Override the parent's perform action with a check for exists
        Args:
            web_element: Element to check if it exists.
            *args: Unused arguments to follow the override signature.

        Returns: None

        """
        return web_element.is_displayed()

    def __str__(self):
        """
        String representation of this action.
        Returns:

        """
        return "IS_EXISTS"
