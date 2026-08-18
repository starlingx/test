import fnmatch
import os
from datetime import datetime

import pytest

from config.configuration_manager import ConfigurationManager
from framework.database.objects.test_case_result import TestCaseResult
from framework.database.objects.testcase import TestCase
from framework.database.operations.test_case_result_operation import TestCaseResultOperation
from framework.database.operations.test_info_operation import TestInfoOperation
from framework.logging.automation_logger import get_logger
from framework.runner.objects.run_context_manager import RunContextManager
from framework.runner.objects.test_executor_summary import TestExecutorSummary


class ResultCollector:
    """
    Pytest plugin that allows us to get results and add them to the test summary object
    """

    def __init__(self, test_executor_summary: TestExecutorSummary, test: TestCase):
        self.test_executor_summary = test_executor_summary
        self.test = test
        self.start_time = datetime.now()  # start time for the test
        self.failure_file_name = ""
        self.failure_function_name = ""
        self.failure_line_number = ""

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(self, item: any, call: any):
        """
        Called at the end of the pytest test, we then can append the test summary

        Args:
            item (any): the test
            call (any): the stage of the test

        """
        outcome = yield
        report = outcome.get_result()

        # Record where the test went wrong. This is done for every stage so that a failure in
        # setup or teardown is captured as well as one in the test itself.
        if call.excinfo:
            self.parse_failure_location(call.excinfo)

        if report.when == "setup":
            self.test_executor_summary.set_last_result(None)
        elif report.when == "call":
            self.test_executor_summary.set_last_result(report.outcome.upper())
        # create final test result and update db if needed
        elif report.when == "teardown":
            # if the teardown failed, update the result of the test
            if report.outcome.upper() == "FAILED":
                self.test_executor_summary.set_last_result(report.outcome.upper())
            self.test_executor_summary.increment_test_index()
            self.test_executor_summary.append_tests_summary(f"{self.test_executor_summary.get_last_result()}      " f"{item.nodeid}")

            # update db if configured
            if ConfigurationManager.get_database_config().use_database():
                self.update_result_in_database(self.test_executor_summary.get_last_result())

    def parse_failure_location(self, exception_info: any) -> None:
        """
        Works out the file, function and line that the test case failed on.

        The innermost keyword frame is preferred, since that is where the test case actually
        went wrong. If the traceback holds no keyword frame, the innermost frame is used.

        Args:
            exception_info (any): the exception info, from call.excinfo.

        """
        try:
            tracebacks = exception_info.traceback
            if not tracebacks:
                return

            selected_trace = None
            for trace in reversed(tracebacks):
                if fnmatch.fnmatch(str(trace.path), "*keywords*"):
                    selected_trace = trace
                    break

            if not selected_trace:
                selected_trace = tracebacks[-1]

            self.failure_file_name = os.path.basename(str(selected_trace.path))
            self.failure_function_name = selected_trace.name
            self.failure_line_number = str(selected_trace.relline)
        except Exception as exception:
            get_logger().log_error(f"Unable to parse the failure location of {self.test.get_test_name()}: {exception}")

    def get_test_id(self) -> int:
        """
        Resolves the id that the database holds for the test case that just ran.

        The test_info row is written by the test scanner rather than by the run, so the id has to
        be looked up in whichever database we have been pointed at.

        Not every database labels these test cases with the same repository, so a lookup that
        misses is retried under 'ace' before it is given up on.

        Returns:
            int: the test_info id of the test case, None if the database has no entry for it.

        """
        test_info_operation = TestInfoOperation()
        repository = RunContextManager.get_repository()

        test_id = test_info_operation.get_info_test_id(self.test.get_test_name(), self.test.get_test_suite(), repository)
        if test_id or repository == "ace":
            return test_id

        get_logger().log_warning(f"{self.test.get_test_suite()}::{self.test.get_test_name()} is not in the database under the repository {repository}. Looking it up under 'ace' instead.")
        return test_info_operation.get_info_test_id(self.test.get_test_name(), self.test.get_test_suite(), "ace")

    def update_result_in_database(self, outcome: any) -> None:
        """
        Inserts the result of the test case into the database

        Args:
            outcome (any): the result of the test

        """
        # if the test crashes at the start, start time can be empty -- setting so we don't crash db update
        if not self.start_time:
            self.start_time = datetime.now()

        # set values to PASS or FAIL
        if outcome == "PASSED":
            outcome = "PASS"
        else:
            outcome = "FAIL"

        test_id = self.get_test_id()
        if not test_id:
            get_logger().log_error(f"There is no test_info entry for {self.test.get_test_suite()}::{self.test.get_test_name()}. The result of this test case was not recorded.")
            return

        test_case_result = TestCaseResult(test_id, outcome, self.start_time, datetime.now())
        test_case_result.set_session_id(RunContextManager.get_session_id())
        test_case_result.set_jenkins_log_location(RunContextManager.get_jenkins_log_location() or "")
        test_case_result.set_failure_file_name(self.failure_file_name)
        test_case_result.set_failure_function_name(self.failure_function_name)
        test_case_result.set_failure_line_number(self.failure_line_number)

        TestCaseResultOperation().create_test_case_result(test_case_result)
