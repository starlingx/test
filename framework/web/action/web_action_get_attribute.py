"""Web Action to get an attribute value from an element."""

from framework.web.action.web_action import WebAction


class WebActionGetAttribute(WebAction):
    """Class representing the action of getting an attribute value from an element."""

    def perform_action(self, web_element, *args):
        """Get the specified attribute value from the element.

        Args:
            web_element: Element of interest.
            *args: First argument is the attribute name.

        Returns:
            str: The attribute value, or None if not present.
        """
        attribute_name = args[0]
        return web_element.get_attribute(attribute_name)

    def __str__(self):
        """Return string representation of this action.

        Returns:
            str: Action name.
        """
        return "GetAttribute"
