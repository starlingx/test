from framework.web.action.web_action import WebAction


class WebActionSetText(WebAction):
    """
    Class representing a Web action of Setting the text content of an element.
    """

    def perform_action(self, web_element, *args):
        """
        Override the parent's perform action - Clears the text and then sets the text of the web_element to the argument passed in.
        Args:
            web_element: Element to set the text of.
            *args: One 'str' argument; The text to write in the web_element.

        Returns: None

        """
        text_to_set = args[0]
        web_element.clear()
        web_element.send_keys(text_to_set)

    def __str__(self):
        """
        String representation of this action.
        Returns:

        """
        return "SetText"
