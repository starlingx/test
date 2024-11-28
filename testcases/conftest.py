import os

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.logging import log_banners
from framework.logging.automation_logger import configure_testcase_log_handler, get_logger, remove_testcase_handler


def pytest_addoption(parser):
    parser.addoption("--lab_config_file", action="store")
    parser.addoption("--k8s_config_file", action="store")
    parser.addoption("--logger_config_file", action="store")
    parser.addoption("--docker_config_file", action="store")
    parser.addoption("--web_config_file", action="store")
    parser.addoption("--database_config_file", action="store")
    parser.addoption("--rest_api_config_file", action="store")

def pytest_sessionstart(session):
    """
    This is run once at test start up.
    Returns:

    """

    configuration_locations_manager = ConfigurationFileLocationsManager()

    configuration_locations_manager.set_configs_from_pytest_args(session)

    ConfigurationManager.load_configs(configuration_locations_manager)
    log_configuration()


def log_configuration():
    """
    This function will log all the configurations that are loaded
    """

    get_logger().log_debug("----- LOGGER CONFIG -----")
    for config_string in ConfigurationManager.get_logger_config().to_log_strings():
        get_logger().log_debug(config_string)

    get_logger().log_debug("----- LAB CONFIG -----")
    for config_string in ConfigurationManager.get_lab_config().to_log_strings():
        get_logger().log_debug(config_string)


def pytest_runtest_setup(item):
    """
    This will run before any test case starts its execution
    Args:
        item: The test case item that we are about to execute.

    Returns: None

    """

    # add testcase log handler at test start
    configure_testcase_log_handler(ConfigurationManager.get_logger_config(), item.name)
    log_banners.log_test_start_banner(item)


def pytest_runtest_makereport(item, call):
    """
    This Pytest hook gets called after the execution of a test case or test suite.
    Args:
        item: The test case that was executed.
        call: Information about the execution.

    Returns: None

    """

    # Handle Exceptions that happened during the test case.
    if call.excinfo:
        log_exception(call.excinfo)
    if call.when == 'teardown':
        # remove testcase logger file handler at end of each test
        remove_testcase_handler(item.name)


def log_exception(exception_info):
    """
    This function will log the StackTrace of the exception_info passed in.
    Args:
        exception_info (ExceptionInfo): Obtained from call.excinfo in pytest_runtest_makereport

    Returns: None

    """

    get_logger().log_exception("")
    get_logger().log_exception("---------- EXCEPTION ----------")

    full_traceback = exception_info.traceback

    # Remove the Traceback Entries from on_keyword_wrapped_function
    for entry in full_traceback:

        # Skip over the keyword-wrapping-hook
        if entry.name == 'on_keyword_wrapped_function':
            continue

        # Skip over run_engine functions
        filename = entry.path
        relative_filename = os.path.relpath(filename)
        if "_pytest" in relative_filename or "pluggy" in relative_filename:
            continue

        get_logger().log_exception(f"{relative_filename}:{entry.lineno} in {entry.name}")
        get_logger().log_exception(entry.statement)

    get_logger().log_exception(f"EXCEPTION! {exception_info.typename}: {exception_info.value}")
    get_logger().log_exception("")
