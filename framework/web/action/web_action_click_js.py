from typing import Any

from framework.web.action.web_action import WebAction


class WebActionClickJs(WebAction):
    """
    Class representing a Web Click action using JavaScript.
    """

    def perform_action(self, web_element: Any, *args: Any) -> None:
        """
        Override the parent's perform action with a JavaScript click.

        Args:
            web_element (Any): Element to click on.
            *args (Any): Unused arguments to follow the override signature.
        """
        self.webdriver.execute_script("arguments[0].click();", web_element)

    def __str__(self) -> str:
        """
        String representation of this action.
        """
        return "ClickJs"
