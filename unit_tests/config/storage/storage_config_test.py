from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_default_storage_config():
    """
    Tests that the default storage configuration is as expected.

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_storage_config()

    assert default_config is not None, "Default storage config wasn't loaded successfully"
    assert default_config.get_credentials().get_user_name() == "admin", "Default storage username should be admin"
    assert default_config.get_credentials().get_password() == "", "Default storage password should be empty"
    assert default_config.get_storage_array_id() == "", "Default storage array id should be empty"
    assert default_config.get_storage_array_endpoint() == "", "Default storage array endpoint should be empty"
    assert default_config.get_storage_array_nas_name() == "", "Default storage array nas name should be empty"


def test_custom_storage_config():
    """
    Tests that we can load a custom storage configuration.

    """
    custom_file = get_stx_resource_path("unit_tests/config/storage/custom_storage_config.json5")
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_storage_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_storage_config()
    assert custom_config is not None, "Custom storage config wasn't loaded successfully"
    assert custom_config.get_credentials().get_user_name() == "testuser", "The custom config username isn't loaded correctly"
    assert custom_config.get_credentials().get_password() == "testpass", "The custom config password isn't loaded correctly"
    assert custom_config.get_storage_array_id() == "PSxxxxxxxxxxxx", "The custom config storage array id isn't loaded correctly"
    assert custom_config.get_storage_array_endpoint() == "https://10.10.10.10/api/rest", "The custom config storage array endpoint isn't loaded correctly"
    assert custom_config.get_storage_array_nas_name() == "NAS1", "The custom config storage array nas name isn't loaded correctly"
