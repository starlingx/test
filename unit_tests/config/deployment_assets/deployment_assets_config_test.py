from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_default_deployment_assets_config():
    """
    Tests that the default deployment assets configuration is as expected.

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_deployment_assets_config()

    assert default_config is not None, "Default deployment_assets config wasn't loaded successfully"
    assert not default_config.get_controller_deployment_assets().get_bootstrap_file(), "There should be no Boostrap Config for controller"
    assert default_config.get_controller_deployment_assets().get_deployment_config_file() == "/home/sysadmin/deployment-config.yaml", "There should be a Deployment Config for controller"
    assert default_config.get_subcloud_deployment_assets("subcloud1").get_deployment_config_file() == "/home/sysadmin/subcloud-1/subcloud1-deploy-standard.yaml", "There should be a Deployment Config for subcloud1"


def test_custom_deployment_assets_config():
    """
    Tests that we can load a custom lab files configuration.

    """
    custom_file = get_stx_resource_path("unit_tests/config/deployment_assets/custom_deployment_assets_config.json5")
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_deployment_assets_config_file(custom_file)
    configuration_manager.load_configs(config_file_locations)

    custom_config = configuration_manager.get_deployment_assets_config()
    assert custom_config is not None, "Custom deployment assets config wasn't loaded successfully"
    assert custom_config.get_subcloud_deployment_assets("subcloud4").get_install_file() == "Awesome", "The Custom Config file values aren't loaded correctly."
