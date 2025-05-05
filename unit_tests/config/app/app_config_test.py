from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_default_app_config():
    """
    Tests that the default app configuration is as expected.

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_app_config()
    assert default_config is not None, "Default app config wasn't loaded successfully"
    assert default_config.get_base_application_path() == "/usr/local/share/applications/helm/", "default base path was incorrect"
    assert default_config.get_istio_app_name() == "istio", "istio default app name was incorrect"
    assert default_config.get_metric_server_app_name() == "metrics-server", "metric server default name was incorrect"
    assert default_config.get_oidc_app_name() == "oidc-auth-apps", "oidc default app name was incorrect"


def test_custom_app_config():
    """
    Tests that we can load a custom app configuration.
    """
    custom_file = get_stx_resource_path("unit_tests/config/app/custom_app_config.json5")
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_app_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_app_config()
    assert custom_config is not None, "Default app config wasn't loaded successfully"
    assert custom_config.get_base_application_path() == "fake_path", "custom base path was incorrect"
    assert custom_config.get_istio_app_name() == "istio_custom", "istio custom app name was incorrect"
    assert custom_config.get_metric_server_app_name() == "metrics-server_custom", "metric server custom name was incorrect"
    assert custom_config.get_oidc_app_name() == "oidc-auth-apps_custom", "oidc custom app name was incorrect"
