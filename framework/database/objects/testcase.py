class TestCase:
    """Class to hold testcase info."""

    def __init__(self, test_name: str, test_suite: str, priority: str, test_path: str, pytest_node_id: str):
        self.test_name = test_name
        self.test_suite = test_suite
        self.priority = priority
        self.test_path = test_path
        self.pytest_node_id = pytest_node_id

        self.markers: [str] = []
        self.test_info_id = -1
        self.test_case_group_id = -1
        self.is_active = True
        self.run_content_id = -1
        self.repository = "ace"

    def get_test_name(self) -> str:
        """Gets the test name.

        Returns:
            str: The test name.
        """
        return self.test_name

    def get_test_suite(self) -> str:
        """Gets the test suite.

        Returns:
            str: The test suite.
        """
        return self.test_suite

    def get_priority(self) -> str:
        """Gets the priority.

        Returns:
            str: The priority.
        """
        return self.priority

    def get_test_path(self) -> str:
        """Gets the test path.

        Returns:
            str: The test path.
        """
        return self.test_path

    def get_pytest_node_id(self) -> str:
        """Gets the pytest node id.

        Returns:
            str: The pytest node id.
        """
        return self.pytest_node_id

    def get_markers(self) -> [str]:
        """Gets the markers.

        Returns:
            [str]: The markers.
        """
        return self.markers

    def set_markers(self, markers: [str]):
        """Sets the markers.

        Args:
            markers ([str]): The markers.
        """
        self.markers = markers

    def get_test_info_id(self) -> int:
        """Gets the test info id.

        Returns:
            int: The test info id.
        """
        return self.test_info_id

    def set_test_info_id(self, test_info_id: int):
        """Sets the test info id.

        Args:
            test_info_id (int): The test info id.
        """
        self.test_info_id = test_info_id

    def get_test_case_group_id(self) -> int:
        """Gets the test case group id.

        Returns:
            int: The test case group id.
        """
        return self.test_case_group_id

    def set_test_case_group_id(self, test_case_group_id: int):
        """Sets the test case group id.

        Args:
            test_case_group_id (int): The test case group id.
        """
        self.test_case_group_id = test_case_group_id

    def is_testcase_active(self) -> bool:
        """Checks if the test is active.

        Returns:
            bool: True if the test is active.
        """
        return self.is_active

    def set_is_active(self, is_active: bool):
        """Sets the active status.

        Args:
            is_active (bool): The active status.
        """
        self.is_active = is_active

    def set_run_content_id(self, run_content_id: int):
        """Sets the run content id.

        Args:
            run_content_id (int): The run content id.
        """
        self.run_content_id = run_content_id

    def get_run_content_id(self) -> int:
        """Gets the run content id.

        Returns:
            int: The run content id.
        """
        return self.run_content_id

    def get_repository(self) -> str:
        """Gets the repository name.

        Returns:
            str: The repository name.
        """
        return self.repository

    def set_repository(self, repository: str):
        """Sets the repository name.

        Args:
            repository (str): The repository name.
        """
        self.repository = repository
