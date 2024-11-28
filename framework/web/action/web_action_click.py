from framework.web.action.web_action import WebAction


class WebActionClick(WebAction):
    """
    Class representing a Web Click action.
    """

    def perform_action(self, web_element, *args):
        """
        Override the parent's perform action with a click
        Args:
            web_element: Element to click on.
            *args: Unused arguments to follow the override signature.

        Returns: None

        """
        web_element.click()

    def __str__(self):
        """
        String representation of this action.
        Returns:

        """
        return "Click"
