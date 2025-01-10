import time
from time import sleep
from typing import Callable, Any

from framework.logging.automation_logger import get_logger


def validate_equals(observed_value: Any, expected_value: Any, validation_description: str) -> None:
    """
    This function will validate if the observed value matches the expected value with associated logging.

    Args:
        observed_value: Value that we see on the system.
        expected_value: Value that is expected and against which we are asserting.
        validation_description: Description of this validation for logging purposes.

    Returns: None

    """

    if observed_value == expected_value:
        get_logger().log_info(f"Validation Successful - {validation_description}")
    else:
        get_logger().log_error(f"Validation Failed - {validation_description}")
        get_logger().log_error(f"Expected: {expected_value}")
        get_logger().log_error(f"Observed: {observed_value}")
        raise Exception("Validation Failed")


def validate_equals_with_retry(function_to_execute: Callable[[], Any],
                               expected_value: Any,
                               validation_description: str,
                               timeout: int = 30,
                               polling_sleep_time: int = 5,) -> None:
    """
      Validates that function_to_execute will return the expected value in the specified amount of time.

      Args:
        function_to_execute: The function to be executed repeatedly, taking no arguments and returning any value.
        expected_value: The expected return value of the function.
        validation_description: Description of this validation for logging purposes.
        timeout: The maximum time (in seconds) to wait for the match.
        polling_sleep_time: The interval of time to wait between calls to function_to_execute.

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
