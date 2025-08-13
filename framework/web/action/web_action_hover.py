from framework.web.action.web_action import WebAction


class WebActionHover(WebAction):
    """
    Class representing a Web Click action.
    """

    def perform_action(self, web_element, *args):
        """
        Override the parent's perform action with a hover
        Args:
            web_element: Element to hover on.
            *args: Unused arguments to follow the override signature.

        Returns: None

        """
        self.actions.move_to_element(web_element).perform()

    def __str__(self):
        """
        String representation of this action.
        Returns:

        """
        return "Hover"
