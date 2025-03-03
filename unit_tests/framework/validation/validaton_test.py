from config.configuration_file_locations_manager import (
    ConfigurationFileLocationsManager,
)
from config.configuration_manager import ConfigurationManager
from framework.validation.validation import validate_str_contains


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
    try:
        validate_str_contains("observed value contains: <word not found>", "success", "Test that the word success appears")
        assert False, "Validation passed when it should not have"  # if test succeeds, we should never get to this line
    except Exception as e:
        assert e.__str__() == "Validation Failed", "Validation failed as expected."
