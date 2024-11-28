from abc import abstractmethod

from framework.web.web_locator import WebLocator


class WebCondition:
    """
    This is an abstract class that implements conditions that will be added as validation for a successful web action.
    """

    def __init__(self, web_locator: WebLocator):
        """
        Constructor which will instantiate the driver object.
        """

        self.web_locator = web_locator

    def get_web_locator(self) -> WebLocator:
        """
        Getter for the Web locator
        Returns:

        """
        return self.web_locator

    @abstractmethod
    def is_condition_satisfied(self, webdriver) -> bool:
        """
        Abstract Function
        This function will evaluate the web_condition and return True if it is satisfied and False otherwise.

        Args:
            webdriver: Instance of Selenium Web Driver.

        Returns:

        """
        pass

    @abstractmethod
    def __str__(self):
        """
        Forcing child classes to have a nice String representation for the logger.
        Returns:

        """
        return f"Condition on {self.web_locator}"
