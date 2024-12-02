from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_standard_config_loads_successfully():
    """
    Tests that the standard config loads sucessfully
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config() is not None, 'standard template config did not load successfully'


def test_standard_config_loads_floating_ip():
    """
    Tests that the standard config floating ip is loaded
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_floating_ip() == '10.2.3.120', 'floating ip was incorrect'


def test_standard_config_loads_lab_name():
    """
    Tests that the standard config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_lab_name() == 'MyLab', 'Lab name was incorrect'


def test_standard_config_loads_lab_type():
    """
    Tests that the standard config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_lab_type() == 'Standard', 'lab type was incorrect'


def test_standard_config_loads_admin_credentials():
    """
    Tests the standard config admin credentials load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    admin_credentials = configuration_manager.get_lab_config().get_admin_credentials()
    assert admin_credentials is not None, 'error loading admin credentials'
    assert admin_credentials.get_user_name() == 'fake_user', 'User name is incorrect'
    assert admin_credentials.get_password() == 'fake_password', 'Password is incorrect'


def test_standard_config_loads_nodes():
    """
    Tests the standard config nodes load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    nodes = configuration_manager.get_lab_config().get_nodes()
    assert len(list(filter(lambda node: node.get_name() == 'controller-0', nodes))) == 1, 'controller-0 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'controller-1', nodes))) == 1, 'controller-1 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'compute-0', nodes))) == 1, 'compute-0 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'compute-1', nodes))) == 1, 'compute-1 not in nodes'


def test_standard_config_controller_0():
    """
    Tests the standard config controller-0 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('controller-0')
    assert node.get_ip() == '10.2.3.121', 'controller-0 ip is incorrect'
    assert node.get_name() == 'controller-0', 'controller-0 name is incorrect'
    assert node.get_type() == 'Controller', 'controller-0 type is incorrect'


def test_standard_config_controller_1():
    """
    Tests the standard config controller-1 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('controller-1')
    assert node.get_ip() == '10.2.3.122', 'controller-1 ip is incorrect'
    assert node.get_name() == 'controller-1', 'controller-1 name is incorrect'
    assert node.get_type() == 'Controller', 'controller-1 type is incorrect'


def test_standard_config_compute_0():
    """
    Tests the standard config compute-0 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('compute-0')
    assert node.get_ip() == '10.2.3.123', 'compute-0 ip is incorrect'
    assert node.get_name() == 'compute-0', 'compute-0 name is incorrect'
    assert node.get_type() == 'Compute', 'compute-0 type is incorrect'


def test_standard_config_compute_1():
    """
    Tests the standard config compute-1 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('compute-1')
    assert node.get_ip() == '10.2.3.124', 'compute-1 ip is incorrect'
    assert node.get_name() == 'compute-1', 'compute-1 name is incorrect'
    assert node.get_type() == 'Compute', 'compute-1 type is incorrect'


def test_standard_config_ipv4():
    """
    Tests the standard config is loaded as ipv4
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_standard.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().is_ipv6() is False, 'lab is not ipv4'
