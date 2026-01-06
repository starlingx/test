class TestExecutorSummary:
    """
    Test Executor class
    """

    def __init__(self):
        self.test_index: int = 1
        self.tests_summary: list[str] = []
        self.last_result: str | None = None

    def increment_test_index(self):
        """
        Increments the test_index
        Returns: None

        """
        self.test_index = self.test_index + 1

    def get_test_index(self) -> int:
        """
        Getter for the current test_index
        Returns: int

        """
        return self.test_index

    def append_tests_summary(self, test_summary: str):
        """
        This function will add the test_summary specified to the stored list of tests_summary

        Args:
            test_summary (str): The summary line to add.
        Returns: None

        """
        self.tests_summary.append(test_summary)

    def set_tests_summary(self, test_summary: [str]):
        """
        Sets the test summary

        Args:
            test_summary ([str]): the summary lines to set.

        """
        self.tests_summary = test_summary

    def get_tests_summary(self) -> list[str]:
        """
        Getter for the tests_summary

        Returns:
            list[str]: A list of Strings.

        """
        return self.tests_summary

    def set_last_result(self, last_result: str | None):
        """
        Sets the last_result

        Args:
            last_result (str | None): the last result

        Returns: None

        """
        self.last_result = last_result

    def get_last_result(self) -> str | None:
        """
        Gets the last result

        Returns:
            str | None: the last result

        """
        return self.last_result
