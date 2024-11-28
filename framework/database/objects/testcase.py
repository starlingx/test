class TestCase:
    """
    Class to hold testcase info
    """

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

    def get_test_name(self) -> str:
        """
        Getter for name
        Returns: the name

        """
        return self.test_name

    def get_test_suite(self) -> str:
        """
        Getter for test suite
        Returns:

        """
        return self.test_suite

    def get_priority(self) -> str:
        """
        Getter for priority
        Returns:

        """
        return self.priority

    def get_test_path(self) -> str:
        """
        Getter for execution location
        Returns: the execution location

        """
        return self.test_path

    def get_pytest_node_id(self) -> str:
        """
        Getter for pytest node id
        Returns:

        """
        return self.pytest_node_id

    def get_markers(self) -> [str]:
        """
        Getter for markers
        Returns: the markers

        """
        return self.markers

    def set_markers(self, markers: [str]):
        """
        Setter for markers
        Args:
            markers (): the markers

        Returns:

        """
        self.markers = markers

    def get_test_info_id(self) -> int:
        """
        Getter for test info id
        Returns:

        """
        return self.test_info_id

    def set_test_info_id(self, test_info_id: int):
        """
        Setter for test info id
        Args:
            test_info_id (): the test info id

        Returns:

        """
        self.test_info_id = test_info_id

    def get_test_case_group_id(self) -> int:
        """
        Getter for test_case group id
        Returns:

        """
        return self.test_case_group_id

    def set_test_case_group_id(self, test_case_group_id: int):
        """
        Getter for test_case_group_id
        Args:
            test_case_group_id (): the test_case_group_id

        Returns:

        """
        self.test_case_group_id = test_case_group_id

    def is_testcase_active(self) -> bool:
        """
        Checks if test is active
        Returns:

        """
        return self.is_active

    def set_is_active(self, is_active: bool):
        """
        Setter for is active
        Args:
            is_active ():

        Returns:

        """
        self.is_active = is_active

    def set_run_content_id(self, run_content_id: int):
        """
        Setter for run content id
        Args:
            run_content_id (): the run content id

        Returns:

        """
        self.run_content_id = run_content_id

    def get_run_content_id(self) -> int:
        """
        Getter for run content id
        Returns:

        """
        return self.run_content_id
