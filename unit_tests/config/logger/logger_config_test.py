import logging
import os

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_default_logger_config():
    """
    Tests that the default logger configuration is as expected.
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_logger_config()
    assert default_config is not None, "Default logger config wasn't loaded successfully"

    home_dir = os.path.expanduser('~')
    subfolder = "AUTOMATION_LOGS"
    log_location = os.path.join(home_dir, subfolder)

    assert default_config.get_log_location() == log_location, "Log Location is incorrect."
    assert default_config.get_console_log_level() == "DEBUG", "Console Log level is incorrect."
    assert default_config.get_console_log_level_value() == logging.DEBUG, " Console Log level value is incorrect."
    assert default_config.get_file_log_level() == "DEBUG", "File Log level is incorrect."
    assert default_config.get_file_log_level_value() == logging.DEBUG, "File Log level value is incorrect."


def test_invalid_console_log_level_config():
    """
    Tests that we can load a custom logger configuration.
    """

    try:
        custom_file = get_stx_resource_path('unit_tests/config/logger/invalid_console_log_level_config.json5')
        configuration_manager = ConfigurationManagerClass()
        config_file_locations = ConfigurationFileLocationsManager()
        config_file_locations.set_logger_config_file(custom_file)
        configuration_manager.load_configs(config_file_locations)
        assert False, "There should be an exception when we load the configs."
    except ValueError as e:
        assert "The provided Console Log Level is invalid." in str(e)


def test_invalid_file_log_level_config():
    """
    Tests that we can load a custom logger configuration.
    """

    try:
        custom_file = get_stx_resource_path('unit_tests/config/logger/invalid_file_log_level_config.json5')
        configuration_manager = ConfigurationManagerClass()
        config_file_locations = ConfigurationFileLocationsManager()
        config_file_locations.set_logger_config_file(custom_file)
        configuration_manager.load_configs(config_file_locations)
        assert False, "There should be an exception when we load the configs."
    except ValueError as e:
        assert "The provided File Log Level is invalid." in str(e)


def test_custom_logger_config():
    """
    Tests that we can load a custom logger configuration.
    """

    custom_file = get_stx_resource_path('unit_tests/config/logger/custom_logger_config.json5')
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_logger_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_logger_config()
    assert custom_config is not None, "Custom logger config wasn't loaded successfully"
    assert custom_config.get_log_location() == "/home/user/custom_log_location", "Log Location is incorrect."
    assert custom_config.get_console_log_level() == "DEBUG", "Console Log level is incorrect."
    assert custom_config.get_console_log_level_value() == logging.DEBUG, "Console Log level value is incorrect."
    assert custom_config.get_file_log_level() == "DEBUG", "File Log level is incorrect."
    assert custom_config.get_file_log_level_value() == logging.DEBUG, "File Log level value is incorrect."
