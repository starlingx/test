from datetime import datetime

import pytest

from config.configuration_manager import ConfigurationManager
from framework.database.objects.test_case_result import TestCaseResult
from framework.database.objects.testcase import TestCase
from framework.database.operations.run_content_operation import RunContentOperation
from framework.database.operations.test_case_result_operation import TestCaseResultOperation
from framework.runner.objects.test_executor_summary import TestExecutorSummary


class ResultCollector:
    """
    Pytest plugin that allows us to get results and add them to the test summary object
    """

    def __init__(self, test_executor_summary: TestExecutorSummary, test: TestCase, test_case_result_id: int = None):
        self.test_executor_summary = test_executor_summary
        self.test = test
        self.start_time = datetime.now()  # start time for the test
        self.test_case_result_id = test_case_result_id

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
        if report.when == "call":
            self.test_executor_summary.increment_test_index()
            self.test_executor_summary.append_tests_summary(f"{report.outcome}      " f"{item.nodeid}")
            if ConfigurationManager.get_database_config().use_database():
                self.update_result_in_database(
                    report.outcome.upper(),
                )

    def update_result_in_database(self, outcome: any):
        """
        Updates the result in the database

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

        # if we've been given a testcase result id, update the result and don't create a new one
        if self.test_case_result_id:
            test_case_result = TestCaseResult(-1, outcome, self.start_time, datetime.now())
            test_case_result.set_test_case_result_id(self.test_case_result_id)
            TestCaseResultOperation().update_test_case_result(test_case_result)

        else:
            # we don't have a result yet so create one
            test_case_result = TestCaseResult(self.test.get_test_info_id(), outcome, self.start_time, datetime.now())
            TestCaseResultOperation().create_test_case_result(test_case_result)
            RunContentOperation().update_execution_status(self.test.get_run_content_id(), outcome)
