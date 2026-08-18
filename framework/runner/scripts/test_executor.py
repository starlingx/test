import os
import threading
import time
from optparse import OptionParser
from typing import Optional

import pytest

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.database.objects.testcase import TestCase
from framework.database.operations.run_content_operation import RunContentOperation
from framework.database.operations.run_operation import RunOperation
from framework.database.operations.test_plan_operation import TestPlanOperation
from framework.logging.automation_logger import get_logger
from framework.pytest_plugins.result_collector import ResultCollector
from framework.runner.objects.test_capability_matcher import TestCapabilityMatcher
from framework.runner.objects.test_executor_summary import TestExecutorSummary
from testcases.conftest import log_configuration


def execute_test(test: TestCase, test_executor_summary: TestExecutorSummary, session_id: Optional[str] = None, jenkins_log_location: Optional[str] = None, repository: Optional[str] = None):
    """
    Executes a test case using pytest.

    Args:
        test (TestCase): The test case to execute.
        test_executor_summary (TestExecutorSummary): The test executor summary object.
        session_id (Optional[str], optional): The session that the result of this test case belongs to. Defaults to None.
        jenkins_log_location (Optional[str], optional): The URL of the jenkins job that started this run. Defaults to None.
        repository (Optional[str], optional): The repository that owns this test case. Defaults to None.

    """
    result_collector = ResultCollector(test_executor_summary, test)
    pytest_args = ConfigurationManager.get_config_pytest_args()
    pytest_args.append(test.get_pytest_node_id())
    if session_id:
        pytest_args.append(f"--session_id={session_id}")
    if jenkins_log_location:
        pytest_args.append(f"--jenkins_log_location={jenkins_log_location}")
    if repository:
        pytest_args.append(f"--repository={repository}")

    pytest.main(pytest_args, plugins=[result_collector])


def log_summary(test_executor_summary: TestExecutorSummary):
    """
    Logs the summary of test execution results and the path to the log directory.

    This function processes the test summary provided by `TestExecutorSummary`, logs each
    line of the summary, and logs the location of the log directory.

    Args:
        test_executor_summary (TestExecutorSummary): The summary object containing the test execution results.

    """
    get_logger().log_info("")
    get_logger().log_info("")
    get_logger().log_info("Results Summary:")
    for summary_line in test_executor_summary.get_tests_summary():
        get_logger().log_info(summary_line)
    get_logger().log_info("")
    get_logger().log_info(f"Logs Path: {get_logger().get_log_folder()}")


def main():
    """
    Given the lab configuration, it will run all tests in the given folder that matches the lab capabilities

    """

    parser = OptionParser()

    parser.add_option(
        "--tests_location",
        action="store",
        type="str",
        dest="tests_location",
        help="the location of the tests",
    )

    parser.add_option(
        "--test_plan_id",
        action="store",
        type="str",
        dest="test_plan_id",
        help="the test plan id of the tests to run",
    )

    parser.add_option("--test_case_result_id", action="store", type="int", dest="test_case_result_id", help="deprecated and ignored, the id for the testcase result")

    parser.add_option("--session_id", action="store", type="str", dest="session_id", help="the id of the session that the results belong to")

    parser.add_option("--jenkins_log_location", action="store", type="str", dest="jenkins_log_location", help="the URL of the jenkins job that started this run")
    parser.add_option("--repository", action="store", type="str", dest="repository", help="the repository that owns the test cases of this run")

    configuration_locations_manager = ConfigurationFileLocationsManager()
    configuration_locations_manager.set_configs_from_options_parser(parser)
    ConfigurationManager.load_configs(configuration_locations_manager)
    log_configuration()

    options, args = parser.parse_args()

    # A session id means the caller already knows which test cases it wants us to run and told
    # us with --tests_location. Without one, this is a standalone run and the test cases come
    # from the test plan in the database.
    session_id = options.session_id
    jenkins_log_location = options.jenkins_log_location
    repository = options.repository

    test_capability_matcher = TestCapabilityMatcher(ConfigurationManager.get_lab_config())

    if ConfigurationManager.get_database_config().use_database() and not session_id:
        if not options.test_plan_id:
            raise "You must specify a --test_plan_id that points to the test plan to run from"

        test_plan = TestPlanOperation().get_test_plan(options.test_plan_id)
        run_id = RunOperation().create_run(test_plan.get_test_plan_name(), test_plan.get_run_type_id(), "24.09")  # need to decide on where this comes from
        RunContentOperation().create_run_content(options.test_plan_id, run_id)

        tests = test_capability_matcher.get_list_of_tests_from_db(run_id)
    else:
        if not options.tests_location:
            raise "You must specify a --tests_location that points to the folder for the tests"
        tests = test_capability_matcher.get_list_of_tests(options.tests_location)

    test_executor_summary = TestExecutorSummary()

    if not tests:
        test_executor_summary.append_tests_summary("There is no available test case to run that match the lab's capabilities.")
        test_executor_summary.append_tests_summary("Please review your lab configuration file.")

    for test in tests:
        execute_test(test, test_executor_summary, session_id, jenkins_log_location, repository)

    log_summary(test_executor_summary)

    # Force exit after 10 seconds if process doesn't terminate naturally
    def force_exit_timer():
        time.sleep(10)
        get_logger().log_warning("Process did not exit naturally, forcing exit...")
        os._exit(0)

    timer_thread = threading.Thread(target=force_exit_timer, daemon=True)
    timer_thread.start()

    return 0


if __name__ == "__main__":
    """
    Main Launcher
    """
    exit(main())
