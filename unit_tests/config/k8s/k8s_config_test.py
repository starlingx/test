from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass


def test_default_k8s_config():
    """
    Tests that the default k8s configuration is as expected.

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_k8s_config()

    assert default_config is not None, "Default logger config wasn't loaded successfully"
    assert default_config.get_kubeconfig() == "/etc/kubernetes/admin.conf", "kubeconfig is incorrect"
