from datetime import datetime

from framework.logging.automation_logger import get_logger
from framework.runner.objects.run_host_info import RunHostInfo


class TestCaseResult:
    """
    Class for test case result
    """

    def __init__(self, test_info_id: int, execution_result: str, start_time: datetime, end_time: datetime):
        self.test_info_id = test_info_id
        self.execution_result = execution_result
        self.start_time = start_time
        self.end_time = end_time

        self.log_hostname = RunHostInfo.get_host_ip()
        self.log_location = get_logger().get_test_case_log_dir()
        self.test_case_result_id = -1
        self.duration = 0
        self.test_run_execution_id = -1

    def get_test_info_id(self) -> int:
        """
        Getter for test info id
        Returns:

        """
        return self.test_info_id

    def get_execution_result(self) -> str:
        """
        Getter for execution result
        Returns:

        """
        return self.execution_result

    def get_start_time(self) -> datetime:
        """
        Getter for start time
        Returns:

        """
        return self.start_time

    def get_end_time(self) -> datetime:
        """
        Getter for end time
        Returns:

        """
        return self.end_time

    def get_duration(self) -> int:
        """
        Getter for duration
        Returns:

        """
        return self.duration

    def set_duration(self, duration: int):
        """
        Setter for duration
        Args:
            duration ():

        Returns:

        """
        self.duration = duration

    def get_test_case_result_id(self) -> int:
        """
        Getter for test case result id
        Returns:

        """
        return self.test_case_result_id

    def set_test_case_result_id(self, test_case_result_id: int):
        """
        Setter for test case result id
        Args:
            test_case_result_id (): the test case result id

        Returns:

        """
        self.test_case_result_id = test_case_result_id

    def get_test_run_execution_id(self) -> int:
        """
        Getter for test run execution id
        Returns:

        """
        return self.test_run_execution_id

    def set_test_run_execution_id(self, test_run_execution_id: int):
        """
        Setter for test run execution id
        Args:
            test_run_execution_id (): the test run execution id

        Returns:

        """
        self.test_run_execution_id = test_run_execution_id
