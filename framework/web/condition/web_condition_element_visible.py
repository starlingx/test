from framework.web.condition.web_condition import WebCondition


class WebConditionElementVisible(WebCondition):
    """
    This Web Condition will check if the WebElement is Visible on the screen.
    """

    def is_condition_satisfied(self, webdriver) -> bool:
        """
        This function will evaluate the web_condition and return True if it is satisfied and False otherwise.

        Returns:

        """

        web_element = webdriver.find_elements(self.get_web_locator().get_by(), self.get_web_locator().get_locator())
        is_element_found = len(web_element) > 0

        return is_element_found

    def __str__(self):
        """
        Nice String representation for this condition.
        Returns:

        """
        return f"ElementVisible - {self.get_web_locator()}"
