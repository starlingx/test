import time
from time import sleep
from typing import Any, Callable

from framework.logging.automation_logger import get_logger
from framework.validation.validation_response import ValidationResponse


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
) -> object:
    """
    Validates that function_to_execute will return the expected value in the specified amount of time.

    Args:
      function_to_execute (Callable[[], Any]): The function to be executed repeatedly, taking no arguments and returning any value.
      expected_value (Any): The expected return value of the function.
      validation_description (str): Description of this validation for logging purposes.
      timeout (int): The maximum time (in seconds) to wait for the match.
      polling_sleep_time (int): The interval of time to wait between calls to function_to_execute.

    Returns:
        object: Returns the value_to_return of the ValidationResponse associated with the function_to_execute.

    """
    get_logger().log_info(f"Attempting Validation - {validation_description}")
    end_time = time.time() + timeout

    # Attempt the validation
    while True:

        # Compute the actual value that we are trying to validate.
        result = function_to_execute()
        if isinstance(result, ValidationResponse):
            value_to_validate = result.get_value_to_validate()
            value_to_return = result.get_value_to_return()
        else:
            value_to_validate = result
            value_to_return = result

        if value_to_validate == expected_value:
            get_logger().log_info(f"Validation Successful - {validation_description}")
            return value_to_return
        else:
            get_logger().log_info("Validation Failed")
            get_logger().log_info(f"Expected: {expected_value}")
            get_logger().log_info(f"Observed: {value_to_validate}")

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
) -> object:
    """
    This function will validate if the observed value contains the expected value.

    Args:
        function_to_execute (Callable[[], Any]): The function to be executed repeatedly, taking no arguments and returning any value.
        expected_value(str): the value we are expecting to see in the observed value str.
        validation_description (str): Description of this validation for logging purposes.
        timeout (int): The maximum time (in seconds) to wait for the match.
        polling_sleep_time (int): The interval of time to wait between calls to function_to_execute.

    Returns:
        object: Returns the value_to_return of the ValidationResponse associated with the function_to_execute.

    Raises:
        Exception: when validate fails

    """
    get_logger().log_info(f"Attempting Validation - {validation_description}")
    end_time = time.time() + timeout

    # Attempt the validation
    while True:

        # Compute the actual value that we are trying to validate.
        result = function_to_execute()
        if isinstance(result, ValidationResponse):
            value_to_validate = result.get_value_to_validate()
            value_to_return = result.get_value_to_return()
        else:
            value_to_validate = result
            value_to_return = result

        if expected_value in value_to_validate:
            get_logger().log_info(f"Validation Successful - {validation_description}")
            return value_to_return
        else:
            get_logger().log_info("Validation Failed")
            get_logger().log_info(f"Expected: {expected_value}")
            get_logger().log_info(f"Observed: {value_to_validate}")

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


def validate_list_contains_with_retry(
    function_to_execute: Callable[[], Any],
    expected_values: Any,
    validation_description: str,
    timeout: int = 30,
    polling_sleep_time: int = 5,
) -> object:
    """
    This function will validate if the observed value contains the expected value.

    Args:
        function_to_execute (Callable[[], Any]): The function to be executed repeatedly, taking no arguments and returning any value.
        expected_values (Any): the list of expected values.
        validation_description (str): Description of this validation for logging purposes.
        timeout (int): The maximum time (in seconds) to wait for the match.
        polling_sleep_time (int): The interval of time to wait between calls to function_to_execute.


    Returns:
        object: Returns the value_to_return of the ValidationResponse associated with the function_to_execute.

    Raises:
        Exception: when validate fails

    """
    get_logger().log_info(f"Attempting Validation - {validation_description}")
    end_time = time.time() + timeout

    # Attempt the validation
    while True:

        # Compute the actual value that we are trying to validate.
        result = function_to_execute()
        if isinstance(result, ValidationResponse):
            value_to_validate = result.get_value_to_validate()
            value_to_return = result.get_value_to_return()
        else:
            value_to_validate = result
            value_to_return = result

        if value_to_validate in expected_values:
            get_logger().log_info(f"Validation Successful - {validation_description}")
            return value_to_return
        else:
            get_logger().log_info("Validation Failed")
            get_logger().log_info(f"Expected: {expected_values}")
            get_logger().log_info(f"Observed: {value_to_validate}")

            if time.time() < end_time:
                get_logger().log_info(f"Retrying in {polling_sleep_time}s")
                sleep(polling_sleep_time)
                # Move on to the next iteration
            else:
                raise TimeoutError(f"Timeout performing validation - {validation_description}")


def validate_greater_than(observed_value: int, baseline_value: int, validation_description: str) -> None:
    """
    This function will validate if the observed value is greater then the baseline value.

    Args:
        observed_value (int): Value that we see on the system.
        baseline_value (int): Value that we want to see if the observed value is greater than
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: raised when validate fails

    """
    if observed_value > baseline_value:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error(f"Baseline: {baseline_value}")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_none(observed_value: Any, validation_description: str) -> None:
    """
    This function will validate if the observed value is none.

    Args:
        observed_value (Any): Value that we see on the system.
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: raised when validate fails

    """
    if observed_value is None:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error("Expected: None")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_not_none(observed_value: Any, validation_description: str) -> None:
    """
    This function will validate if the observed value is not none.

    Args:
        observed_value (Any): Value that we see on the system.
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: raised when validate fails

    """
    if observed_value is not None:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error("Expected: Not None")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_is_digit(observed_value: str, validation_description: str) -> None:
    """
    This function will validate if the observed value is a digit string.

    Args:
        observed_value (str): Value that we see on the system.
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: raised when validate fails

    """
    if observed_value.isdigit():
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error("Expected: Digit string")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_greater_than_or_equal(observed_value: int, baseline_value: int, validation_description: str) -> None:
    """
    This function will validate if the observed value is greater than or equal to the baseline value.

    Args:
        observed_value (int): Value that we see on the system.
        baseline_value (int): Value that we want to see if the observed value is greater than or equal to
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: raised when validate fails

    """
    if observed_value >= baseline_value:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error(f"Baseline: {baseline_value}")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_less_than_or_equal(observed_value: int, baseline_value: int, validation_description: str) -> None:
    """
    This function will validate if the observed value is less than or equal to the baseline value.

    Args:
        observed_value (int): Value that we see on the system.
        baseline_value (int): Value that we want to see if the observed value is less than or equal to
        validation_description (str): Description of this validation for logging purposes.

    Returns: None

    Raises:
        Exception: raised when validate fails

    """
    if observed_value <= baseline_value:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error(f"Baseline: {baseline_value}")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")