import pytest

from config.configuration_file_locations_manager import (
    ConfigurationFileLocationsManager,
)
from config.configuration_manager import ConfigurationManager
from framework.validation.validation import (
    validate_not_equals,
    validate_str_contains,
    validate_str_contains_with_retry,
)


def test_validate_str_contains():
    """
    Validates function validate_str_contains
    """
    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)
    validate_str_contains("observed value contains: success", "success", "Test that the word success appears")


def test_validate_str_contains_fails():
    """
    Validates function validate_str_contains fails when expected
    """
    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)
    with pytest.raises(Exception):
        validate_str_contains("observed value contains: <word not found>", "success", "Test that the word success appears")


def test_validate_str_contains_with_retries():
    """
    Test to validate str contains with retries

    """
    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)
    counter = 0

    def function_for_validate_with_retries():
        nonlocal counter
        if counter == 0:
            counter += 1
            return "this was not what you are looking for"
        else:
            counter = 0
            return "successful"

    validate_str_contains_with_retry(function_for_validate_with_retries, "success", "validate success string", polling_sleep_time=0.01)


def test_validate_str_contains_with_retries_fail():
    """
    Test to validate str contains with retries when it fails

    """
    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    def function_for_validate_with_retries():
        return "this was not what you are looking for"

    with pytest.raises(TimeoutError):
        validate_str_contains_with_retry(function_for_validate_with_retries, "success", "validate success string", polling_sleep_time=0.01, timeout=0.05)


def test_validate_not_equals_str():
    """
    Tests the validate not equals function with a string

    """
    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)
    validate_not_equals("success", "unsuccess", "Test that the words success and unsuccess are not equal")


def test_validate_not_equals_list():
    """
    Tests the validate not equals function with a list

    """
    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    list1 = ["success", "successful"]
    list2 = ["success", "unsuccessful"]

    validate_not_equals(list1, list2, "Test that the lists are not equal")
