class RunContent:
    """
    Class for Test Run Content
    """

    def __init__(self, run_id: int, session_info_id: int, test_info_id: int):
        self.run_id = run_id
        self.session_info_id = session_info_id
        self.test_info_id = test_info_id

        self.run_content_id = -1
        self.run_content_execution_status = "NOT_RUN"
        self.execution_fail_count = 0
        self.test_case_group_id = -1

    def get_run_id(self) -> int:
        """
        Getter for run id
        Returns: the run id

        """
        return self.run_id

    def get_session_info_id(self) -> int:
        """
        Getter for session info id
        Returns: the session info id

        """
        return self.session_info_id

    def get_test_info_id(self) -> int:
        """
        Getter for test info id
        Returns: the test info id

        """
        return self.test_info_id

    def get_run_content_id(self) -> int:
        """
        Getter for run content id
        Returns: the run content id

        """
        return self.run_content_id

    def set_run_content_id(self, run_content_id: int):
        """
        Setter for run content id
        Args:
            run_content_id (): the run content id

        Returns:

        """
        self.run_content_id = run_content_id

    def get_run_content_execution_status(self) -> str:
        """
        Getter for run content execution status
        Returns: the run content execution status

        """
        return self.run_content_execution_status

    def set_run_content_execution_status(self, run_content_execution_status):
        """
        Setter for run content execution status
        Args:
            run_content_execution_status (): the run content execution status

        Returns:

        """
        self.run_content_execution_status = run_content_execution_status

    def get_execution_fail_count(self) -> int:
        """
        Getter for execution fail count
        Returns: the execution fail count

        """
        return self.execution_fail_count

    def set_execution_fail_count(self, execution_fail_count: int):
        """
        Setter for execution fail count
        Args:
            execution_fail_count (): the execution fail count

        Returns:

        """
        self.execution_fail_count = execution_fail_count

    def get_test_case_group_id(self) -> int:
        """
        Getter for test case group id
        Returns: the test case group id

        """
        return self.test_case_group_id

    def set_test_case_group_id(self, test_case_group_id: int):
        """
        Setter for test case group id
        Args:
            test_case_group_id (): the test case group id

        Returns:

        """
        self.test_case_group_id = test_case_group_id
