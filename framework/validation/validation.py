import time
from time import sleep
from typing import Any, Callable

from framework.logging.automation_logger import get_logger


def validate_equals(observed_value: Any, expected_value: Any, validation_description: str) -> None:
    """
    This function will validate if the observed value matches the expected value with associated logging.

    Args:
        observed_value (Any): Value that we see on the system.
        expected_value (Any): Value that is expected and against which we are asserting.
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: raised when validate fails

    """
    if observed_value == expected_value:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error(f"Expected: {expected_value}")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_equals_with_retry(
    function_to_execute: Callable[[], Any],
    expected_value: Any,
    validation_description: str,
    timeout: int = 30,
    polling_sleep_time: int = 5,
) -> None:
    """
    Validates that function_to_execute will return the expected value in the specified amount of time.

    Args:
      function_to_execute (Callable[[], Any]): The function to be executed repeatedly, taking no arguments and returning any value.
      expected_value (Any): The expected return value of the function.
      validation_description (str): Description of this validation for logging purposes.
      timeout (int): The maximum time (in seconds) to wait for the match.
      polling_sleep_time (int): The interval of time to wait between calls to function_to_execute.

    Raises:
        TimeoutError: raised when validate does not equal in the required time

    """
    get_logger().log_info(f"Attempting Validation - {validation_description}")
    end_time = time.time() + timeout

    # Attempt the validation
    while True:

        # Compute the actual value that we are trying to validate.
        result = function_to_execute()

        if result == expected_value:
            get_logger().log_info(f"Validation Successful - {validation_description}")
            return
        else:
            get_logger().log_info("Validation Failed")
            get_logger().log_info(f"Expected: {expected_value}")
            get_logger().log_info(f"Observed: {result}")

            if time.time() < end_time:
                get_logger().log_info(f"Retrying in {polling_sleep_time}s")
                sleep(polling_sleep_time)
                # Move on to the next iteration
            else:
                raise TimeoutError(f"Timeout performing validation - {validation_description}")


def validate_not_equals(observed_value: Any, expected_value: Any, validation_description: str) -> None:
    """
    This function will validate if the observed value does not match the expected value with associated logging.

    Args:
        observed_value (Any): Value that we see on the system.
        expected_value (Any): Value that is not expected and against which we are asserting.
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: raised when validate fails

    """
    if observed_value != expected_value:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error(f"Expected: {expected_value}")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_str_contains(observed_value: str, expected_value: str, validation_description: str) -> None:
    """
    This function will validate if the observed value contains the expected value.

    Args:
        observed_value(str): Value that we see on the system.
        expected_value(str): the value we are expecting to see in the observed value str.
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: when validate fails

    """
    if expected_value in observed_value:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error(f"Expected: {expected_value}")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_str_contains_with_retry(
    function_to_execute: Callable[[], Any],
    expected_value: str,
    validation_description: str,
    timeout: int = 30,
    polling_sleep_time: int = 5,
) -> None:
    """
    This function will validate if the observed value contains the expected value.

    Args:
        function_to_execute (Callable[[], Any]): The function to be executed repeatedly, taking no arguments and returning any value.
        expected_value(str): the value we are expecting to see in the observed value str.
        validation_description (str): Description of this validation for logging purposes.
        timeout (int): The maximum time (in seconds) to wait for the match.
        polling_sleep_time (int): The interval of time to wait between calls to function_to_execute.


    Returns: None

    Raises:
        Exception: when validate fails

    """
    get_logger().log_info(f"Attempting Validation - {validation_description}")
    end_time = time.time() + timeout

    # Attempt the validation
    while True:

        # Compute the actual value that we are trying to validate.
        result = function_to_execute()

        if expected_value in result:
            get_logger().log_info(f"Validation Successful - {validation_description}")
            return
        else:
            get_logger().log_info("Validation Failed")
            get_logger().log_info(f"Expected: {expected_value}")
            get_logger().log_info(f"Observed: {result}")

            if time.time() < end_time:
                get_logger().log_info(f"Retrying in {polling_sleep_time}s")
                sleep(polling_sleep_time)
                # Move on to the next iteration
            else:
                raise TimeoutError(f"Timeout performing validation - {validation_description}")


def validate_list_contains(observed_value: Any, expected_values: Any, validation_description: str) -> None:
    """
    This function validates if the observed value matches ANY of the expected values with associated logging.

    Args:
        observed_value (Any): Value that we see on the system.
        expected_values (Any): A LIST of values that are expected. The observed value is checked against each of these.
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: if the validation fails.
    """
    if observed_value in expected_values:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error(f"Expected: {expected_values}")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")
