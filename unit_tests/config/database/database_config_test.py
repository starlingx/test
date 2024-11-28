from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass


def test_default_database_config():
    """
    Tests that the default database configuration is as expected.
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_database_config()
    assert default_config is not None, "Default database config wasn't loaded successfully"
    assert not default_config.use_database(), "Use database value is incorrect."
    assert default_config.get_host_name() == "fake_host_name", "Host name is incorrect."
    assert default_config.get_db_name() == "fake_db_name", "DB name is incorrect."
    assert default_config.get_db_port() == 5432, "DB Port is incorrect"
    assert default_config.get_user_name() == "fake_user", "User name is incorrect"
    assert default_config.get_password() == "fakePassword$", "Password is incorrect."


def test_custom_database_config():
    """
    Tests that we can load a custom database configuration.
    """

    custom_file = 'unit_tests/config/database/custom_database_config.json5'
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_database_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_database_config()
    assert custom_config is not None, "Custom database config wasn't loaded successfully"
    assert custom_config.use_database(), "Use database value is incorrect."
    assert custom_config.get_host_name() == "custom_host_name", "Host name is incorrect."
    assert custom_config.get_db_name() == "custom_db_name", "DB name is incorrect."
    assert custom_config.get_db_port() == 5432, "DB Port is incorrect"
    assert custom_config.get_user_name() == "custom_user", "User name is incorrect"
    assert custom_config.get_password() == "customPassword$", "Password is incorrect."
