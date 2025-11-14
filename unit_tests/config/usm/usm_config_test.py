from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_default_usm_config():
    """
    Tests that the default usm configuration is as expected.

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_usm_config()
    assert default_config is not None, "Default usm config wasn't loaded successfully"
    assert default_config.get_iso_path() == "/opt/software/starlingx.iso", "ISO path was incorrect"


def test_custom_usm_config():
    """
    Tests that we can load a custom usm configuration.
    """
    custom_file = get_stx_resource_path("config/usm/files/default.json5")
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_usm_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_usm_config()
    assert custom_config is not None, "Custom usm config wasn't loaded successfully"
    assert custom_config.get_iso_path() == "/opt/software/starlingx.iso", "ISO path was incorrect"
