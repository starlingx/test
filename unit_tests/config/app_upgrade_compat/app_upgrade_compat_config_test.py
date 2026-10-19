import pytest

from config.app_upgrade_compat.objects.app_upgrade_compat_config import AppUpgradeCompatConfig
from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def _load_default_config() -> AppUpgradeCompatConfig:
    """
    Load the default application upgrade compatibility config.

    Returns:
        AppUpgradeCompatConfig: the configuration built from the shipped default file.

    """
    configuration_manager = ConfigurationManagerClass()
    configuration_manager.load_configs(ConfigurationFileLocationsManager())
    return configuration_manager.get_app_upgrade_compat_config()


def test_default_app_upgrade_compat_config():
    """
    Tests that the default application upgrade compatibility configuration is as expected.

    """
    default_config = _load_default_config()
    assert default_config is not None, "Default app upgrade compat config wasn't loaded successfully"
    assert default_config.get_to_version() == "26.10", "Target version was incorrect"


def test_custom_app_upgrade_compat_config():
    """
    Tests that we can load a custom application upgrade compatibility configuration.

    """
    custom_file = get_stx_resource_path("config/app_upgrade_compat/files/default.json5")
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_app_upgrade_compat_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_app_upgrade_compat_config()
    assert custom_config is not None, "Custom app upgrade compat config wasn't loaded successfully"
    assert custom_config.get_to_version() == "26.10", "Target version was incorrect"


@pytest.mark.parametrize("app_key", ["cert-manager", "oran-o2"])
def test_configured_applications_resolve(app_key: str):
    """
    Tests that every configured application exposes an application name and a namespace.

    Args:
        app_key(str): the configured application key under test.

    """
    default_config = _load_default_config()
    assert default_config.get_app_name(app_key), f"Application {app_key} had no app_name"
    assert default_config.get_namespace(app_key), f"Application {app_key} had no namespace"


def test_unconfigured_application_raises():
    """
    Tests that reading an application the configuration does not carry raises rather than returning None.

    A test asking for an application that is not configured has a bug in the test, not a missing
    default, so the configuration refuses instead of handing back an empty value.

    """
    default_config = _load_default_config()
    with pytest.raises(ValueError):
        default_config.get_app_name("not-a-configured-application")
    with pytest.raises(ValueError):
        default_config.get_namespace("not-a-configured-application")
