class TestExecutorSummary:

    def __init__(self):
        self.test_index = 1
        self.tests_summary = []

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

    def get_tests_summary(self) -> [str]:
        """
        Getter for the tests_summary
        Returns: A list of Strings.

        """
        return self.tests_summary
