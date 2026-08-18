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
        self.jenkins_log_location = ""
        self.failure_file_name = ""
        self.failure_function_name = ""
        self.failure_line_number = ""

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

    def get_jenkins_log_location(self) -> str:
        """
        Getter for jenkins log location

        Returns:
            str: the URL of the jenkins job that ran this test case

        """
        return self.jenkins_log_location

    def set_jenkins_log_location(self, jenkins_log_location: str):
        """
        Setter for jenkins log location

        Args:
            jenkins_log_location (str): the URL of the jenkins job that ran this test case

        """
        self.jenkins_log_location = jenkins_log_location

    def get_failure_file_name(self) -> str:
        """
        Getter for failure file name

        Returns:
            str: the name of the file that the test case failed in

        """
        return self.failure_file_name

    def set_failure_file_name(self, failure_file_name: str):
        """
        Setter for failure file name

        Args:
            failure_file_name (str): the name of the file that the test case failed in

        """
        self.failure_file_name = failure_file_name

    def get_failure_function_name(self) -> str:
        """
        Getter for failure function name

        Returns:
            str: the name of the function that the test case failed in

        """
        return self.failure_function_name

    def set_failure_function_name(self, failure_function_name: str):
        """
        Setter for failure function name

        Args:
            failure_function_name (str): the name of the function that the test case failed in

        """
        self.failure_function_name = failure_function_name

    def get_failure_line_number(self) -> str:
        """
        Getter for failure line number

        Returns:
            str: the line number that the test case failed on

        """
        return self.failure_line_number

    def set_failure_line_number(self, failure_line_number: str):
        """
        Setter for failure line number

        Args:
            failure_line_number (str): the line number that the test case failed on

        """
        self.failure_line_number = failure_line_number

    def get_log_hostname(self) -> str:
        """
        Getter for log hostname

        Returns:
            str: the ip of the host that holds the logs of this test case

        """
        return self.log_hostname

    def get_log_location(self) -> str:
        """
        Getter for log location

        Returns:
            str: the directory that holds the logs of this test case

        """
        return self.log_location
