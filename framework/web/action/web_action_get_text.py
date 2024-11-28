from framework.web.action.web_action import WebAction


class WebActionGetText(WebAction):
    """
    Class representing the action of getting the text contents of an element.
    """

    def perform_action(self, web_element, *args):
        """
        Override the parent's perform action by getting the text of an element.
        Args:
            web_element: Element of interest.
            *args: Unused arguments to follow the override signature.

        Returns: None

        """

        web_element_text = web_element.text

        # Sometimes, the text is contained in the 'value' attribute of the element.
        if not web_element_text:
            web_element_text = web_element.get_attribute('value')

        return web_element_text

    def __str__(self):
        """
        String representation of this action.
        Returns:

        """
        return "GetText"
