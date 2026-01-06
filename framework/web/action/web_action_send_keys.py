from selenium.webdriver.remote.webelement import WebElement

from framework.web.action.web_action import WebAction


class WebActionSendKeys(WebAction):
    """
    Class representing a Web action of Sending Keys to an element. SetText should be used whenever possible, but for some cases, we need this one.
    """

    def perform_action(self, web_element: WebElement, *args: str) -> None:
        """
        Override the parent's perform action - Sends Keys to a WebElement

        Args:
            web_element (WebElement): Element to send keys to
            *args (str): One 'str' argument; Keys to send

        Returns: None

        """
        text_to_set = args[0]
        web_element.send_keys(text_to_set)

    def __str__(self) -> str:
        """
        String representation of this action.

        Returns:
            str:
        """
        return "SendKeys"
