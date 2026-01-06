from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_default_security_config():
    """
    Tests that the default security configuration is as expected.

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_security_config()
    assert default_config is not None, "Default security config wasn't loaded successfully"
    assert default_config.get_domain_name() == "lab_domain_name", "default domain name was incorrect"


def test_custom_security_config():
    """
    Tests that we can load a custom security configuration.
    """
    custom_file = get_stx_resource_path("unit_tests/config/security/custom_security_config.json5")
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_security_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_security_config()
    assert custom_config is not None, "Custom security config wasn't loaded successfully"
    assert custom_config.get_domain_name() == "fake_domain_name", "Custom dns name was incorrect"
