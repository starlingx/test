from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass


def test_load_config():
    """
    Tests that the default configs are loaded successfully
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config() is not None


def test_invalid_lab_config_file():
    """
    Tests that a proper error message is given when an incorrect lab config file is used

    """

    try:
        configuration_manager = ConfigurationManagerClass()
        config_file_locations = ConfigurationFileLocationsManager()
        config_file_locations.set_lab_config_file('config/lab/files/no_file.json')
        configuration_manager.load_configs(config_file_locations)
        assert False, "There should be an exception when we load the configs."
    except FileNotFoundError as e:
        assert str(e.filename) == "config/lab/files/no_file.json"


def test_invalid_logger_config_file():
    """
    Tests that a proper error message is given when an incorrect logger config file is used

    """

    try:
        configuration_manager = ConfigurationManagerClass()
        config_file_locations = ConfigurationFileLocationsManager()
        config_file_locations.set_logger_config_file('config/logger/files/no_file.json')
        configuration_manager.load_configs(config_file_locations)
        assert False, "There should be an exception when we load the configs."
    except FileNotFoundError as e:
        assert str(e.filename) == "config/logger/files/no_file.json"


def test_invalid_database_config_file():
    """
    Tests that a proper error message is given when an incorrect database config file is used

    """

    try:
        configuration_manager = ConfigurationManagerClass()
        config_file_locations = ConfigurationFileLocationsManager()
        config_file_locations.set_database_config_file('config/database/files/no_file.json5')
        configuration_manager.load_configs(config_file_locations)
        assert False, "There should be an exception when we load the configs."
    except FileNotFoundError as e:
        assert str(e.filename) == "config/database/files/no_file.json5"
