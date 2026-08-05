from datetime import datetime

from framework.logging.automation_logger import get_logger
from framework.runner.objects.run_host_info import RunHostInfo


class TestCaseResult:
    """
    Class for test case result
    """

    def __init__(self, test_id: int, result: str, start_time: datetime, end_time: datetime):
        self.test_id = test_id
        self.result = result
        self.start_time = start_time
        self.end_time = end_time

        self.log_hostname = RunHostInfo.get_host_ip()
        self.log_location = get_logger().get_test_case_log_dir()
        self.test_case_result_id = -1
        self.duration = 0
        self.session_id = None

    def get_test_id(self) -> int:
        """
        Getter for test id

        Returns:
            int: the test id

        """
        return self.test_id

    def get_result(self) -> str:
        """
        Getter for result

        Returns:
            str: the result

        """
        return self.result

    def get_start_time(self) -> datetime:
        """
        Getter for start time

        Returns:
            datetime: the start time

        """
        return self.start_time

    def get_end_time(self) -> datetime:
        """
        Getter for end time

        Returns:
            datetime: the end time

        """
        return self.end_time

    def get_duration(self) -> int:
        """
        Getter for duration

        Returns:
            int: the duration

        """
        return self.duration

    def set_duration(self, duration: int):
        """
        Setter for duration

        Args:
            duration (int): the duration

        """
        self.duration = duration

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

    def get_session_id(self) -> str:
        """
        Getter for session id

        Returns:
            str: the session id

        """
        return self.session_id

    def set_session_id(self, session_id: str):
        """
        Setter for session id

        Args:
            session_id (str): the session id

        """
        self.session_id = session_id
