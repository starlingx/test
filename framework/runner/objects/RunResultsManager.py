class RunResultsManagerClass:
    """
    Singleton class for storing a test_result_id
    """

    def __init__(self):
        self.test_case_result_id = None

    def get_test_case_result_id(self) -> int:
        """
        Getter for test case result id

        Returns:
            int: the test case result id
        """
        return self.test_case_result_id

    def set_test_case_result_id(self, test_case_result_id: int):
        """
        Setter for test case result id

        Args:
            test_case_result_id (int): the test case result id

        """
        self.test_case_result_id = test_case_result_id


RunResultsManager = RunResultsManagerClass()
