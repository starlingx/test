from optparse import OptionParser
import os
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
from framework.resources.resource_finder import get_stx_resource_path
from framework.runner.objects.test_capability_matcher import TestCapabilityMatcher
from framework.runner.objects.test_executor_summary import TestExecutorSummary
from testcases.conftest import log_configuration


def execute_test(test: TestCase, test_executor_summary: TestExecutorSummary, test_case_result_id: Optional[int] = None) -> None:
    """
    Executes a test case using pytest.

    Args:
        test (TestCase): The test case to execute.
        test_executor_summary (TestExecutorSummary): The test executor summary object.
        test_case_result_id (Optional[int], optional): If provided, updates the specified test case result instead of creating a new one. Defaults to None.

    Returns:
        None
    """
    result_collector = ResultCollector(test_executor_summary, test, test_case_result_id)
    pytest_args = ConfigurationManager.get_config_pytest_args()

    node_id = test.get_pytest_node_id().lstrip("/")  # Normalize node_id

    # Ensure we do not prepend "testcases/" for unit tests
    if node_id.startswith("unit_tests/"):
        resolved_path = get_stx_resource_path(node_id)
    else:
        resolved_path = get_stx_resource_path(os.path.join("testcases", node_id))

    pytest_args.append(resolved_path)

    pytest.main(pytest_args, plugins=[result_collector])


def log_summary(test_executor_summary: TestExecutorSummary):
    """
    Logs the summary of test execution results and the path to the log directory.

    This function processes the test summary provided by `TestExecutorSummary`, logs each
    line of the summary, and logs the location of the log directory.

    Args:
        test_executor_summary (TestExecutorSummary): The summary object containing the test
            execution results.

    Returns:
        None
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
    Returns:

    """

    parser = OptionParser()

    parser.add_option(
        '--tests_location',
        action='store',
        type='str',
        dest='tests_location',
        help='the location of the tests',
    )

    parser.add_option(
        '--test_plan_id',
        action='store',
        type='str',
        dest='test_plan_id',
        help='the test plan id of the tests to run',
    )

    parser.add_option('--test_case_result_id', action='store', type='int', dest='test_case_result_id', help='the id for the testcase result')

    configuration_locations_manager = ConfigurationFileLocationsManager()
    configuration_locations_manager.set_configs_from_options_parser(parser)
    ConfigurationManager.load_configs(configuration_locations_manager)
    log_configuration()

    options, args = parser.parse_args()

    test_case_result_id = None
    if options.test_case_result_id:
        test_case_result_id = options.test_case_result_id

    test_capability_matcher = TestCapabilityMatcher(ConfigurationManager.get_lab_config())

    if ConfigurationManager.get_database_config().use_database() and not test_case_result_id:
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
    for test in tests:
        execute_test(test, test_executor_summary, test_case_result_id)

    log_summary(test_executor_summary)


if __name__ == '__main__':
    """
    Main Launcher
    """
    main()
