from framework.web.condition.web_condition import WebCondition


class MockWebCondition(WebCondition):
    """
    This class mocks a Web Condition.
    """

    def __init__(self, number_of_expected_fails: int = 0):
        """
        Constructor which will instantiate the driver object.
        Args:
            number_of_expected_fails: Number of times to throw and exception when perform_action is called.
        """
        super().__init__(None)
        self.number_of_expected_fails = number_of_expected_fails

    def is_condition_satisfied(self, webdriver) -> bool:
        """
        This function will evaluate to True after the number_of_expected_fails.

        Returns:

        """

        if self.number_of_expected_fails > 0:
            self.number_of_expected_fails -= 1
            return False

        return True

    def __str__(self):
        """
        Nice String representation for this condition.
        Returns:

        """
        return "MockCondition"
