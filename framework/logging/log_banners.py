from typing import List

from framework.logging.automation_logger import get_logger


def log_test_start_banner(item):
    """
    This function will log information about the test that we are going to run.
    Args:
        item: The Pytest object representing the test case item that we are about to execute.
              This is the argument taken by 'pytest_runtest_setup'

    Returns: None

    """

    # Access test name and other information from the test item
    test_suite_name = "UNKNOWN"
    test_case_name = "UNKNOWN"
    test_case_full_path = "UNKNOWN"
    try:
        test_case_full_path = item.nodeid

        # e.g. testcases/cloud_platform/hello_world_test.py::test_hello_world
        test_suite_name_array = test_case_full_path.split('/')[-1].split('::')
        test_suite_name = f"Test Suite: {test_suite_name_array[0]}"
        test_case_name = f"Test Case: {test_suite_name_array[-1]}"
    except ValueError:
        get_logger().error(
            f"Failed to extract test_suite_name and test_case_name " f"from {test_case_full_path}"
        )

    # Log a banner showing that we started running a Test Case.
    banner_lines = get_banner(["Starting Test Execution", test_suite_name, test_case_name])
    get_logger().log_info("")
    for line in banner_lines:
        get_logger().log_info(line)
    get_logger().log_info("")


def get_banner(banner_lines: List[str]) -> List[str]:
    """
    This function will build banner to show the lines passed in.
    Args:
        banner_lines: List of lines that you want included in your banner.
                For example: banner_lines = ["TestSuite: my_test_suite", "TestCase: my_test_case"]

    Returns:

        The function will return a list of strings representing the lines of the banner below:

        ************************************
        ***** TestSuite: my_test_suite *****
        ***** TestCase: my_test_case   *****
        ************************************
    """

    banner = []

    # Calculate the length of the longest line
    longest_line_length = max([len(line) for line in banner_lines])

    # Add 5 stars and a space at the beginning. Add a space and 5 stars at the end.
    banner.append("*" * (longest_line_length + 12))
    for line in banner_lines:
        alignment_spaces_required = longest_line_length - len(line)
        banner.append("***** " + line + " " * alignment_spaces_required + " *****")
    banner.append("*" * (longest_line_length + 12))
    return banner
