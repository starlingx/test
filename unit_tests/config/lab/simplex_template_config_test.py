from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_simplex_config_loads_successfully():
    """
    Tests that the simplex config loads successfully
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config() is not None, 'simplex template config did not load successfully'


def test_simplex_config_loads_floating_ip():
    """
    Tests that the simplex config floating ip is loaded
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_floating_ip() == '3851:dc57:c69a:3c77:5d53:29a1:f39c:3d9f', 'floating ip was incorrect'


def test_simplex_config_loads_lab_name():
    """
    Tests that the simplex config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_lab_name() == 'MySimplexLab', 'Lab name was incorrect'


def test_simplex_config_loads_lab_type():
    """
    Tests that the simplex config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_lab_type() == 'Simplex', 'lab type was incorrect'


def test_simplex_config_loads_admin_credentials():
    """
    Tests the simplex config admin credentials load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    admin_credentials = configuration_manager.get_lab_config().get_admin_credentials()
    assert admin_credentials is not None, 'error loading admin credentials'
    assert admin_credentials.get_user_name() == 'fake_user', 'User name is incorrect'
    assert admin_credentials.get_password() == 'fake_password', 'Password is incorrect'


def test_simplex_config_loads_nodes():
    """
    Tests the simplex config nodes load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    nodes = configuration_manager.get_lab_config().get_nodes()
    assert len(list(filter(lambda node: node.get_name() == 'controller-0', nodes))) == 1, 'controller-0 not in nodes'


def test_simplex_config_controller_0():
    """
    Tests the simplex config controller-0 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('controller-0')
    assert node.get_ip() == '3851:dc57:c69a:3c77:5d53:29a1:f39c:3d9f', 'controller-0 ip is incorrect'
    assert node.get_name() == 'controller-0', 'controller-0 name is incorrect'
    assert node.get_type() == 'Controller', 'controller-0 type is incorrect'


def test_simplex_config_ipv4():
    """
    Tests the simplex config is loaded as ipv4
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().is_ipv6(), 'lab is not ipv6'


def test_default_horizon_credentials():
    """
    Tests the simplex config is loaded as ipv4
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_simplex.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_horizon_credentials().get_user_name(), 'admin'
    assert configuration_manager.get_lab_config().get_horizon_credentials().get_password(), 'fake_password'
