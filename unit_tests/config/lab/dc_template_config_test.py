from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.resources.resource_finder import get_stx_resource_path


def test_dc_config_loads_successfully():
    """
    Tests that the dc config loads sucessfully
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config() is not None, 'dc template config did not load successfully'


def test_dc_config_loads_floating_ip():
    """
    Tests that the dc config floating ip is loaded
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_floating_ip() == '10.2.3.125', 'floating ip was incorrect'


def test_dc_config_loads_lab_name():
    """
    Tests that the dc config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_lab_name() == 'MyDCLab', 'Lab name was incorrect'


def test_dc_config_loads_lab_type():
    """
    Tests that the dc config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().get_lab_type() == 'Standard', 'lab type was incorrect'


def test_dc_config_loads_admin_credentials():
    """
    Tests the dc config admin credentials load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    admin_credentials = configuration_manager.get_lab_config().get_admin_credentials()
    assert admin_credentials is not None, 'error loading admin credentials'
    assert admin_credentials.get_user_name() == 'fake_user', 'User name is incorrect'
    assert admin_credentials.get_password() == 'fake_password', 'Password is incorrect'


def test_dc_config_loads_nodes():
    """
    Tests the dc config nodes load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    nodes = configuration_manager.get_lab_config().get_nodes()
    assert len(list(filter(lambda node: node.get_name() == 'controller-0', nodes))) == 1, 'Controller-0 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'controller-1', nodes))) == 1, 'Controller-1 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'compute-0', nodes))) == 1, 'Compute-0 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'compute-1', nodes))) == 1, 'Compute-1 not in nodes'


def test_dc_config_controller_0():
    """
    Tests the dc config controller-0 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('controller-0')
    assert node.get_ip() == '10.2.3.126', 'controller-0 ip is incorrect'
    assert node.get_name() == 'controller-0', 'controller-0 name is incorrect'
    assert node.get_type() == 'Controller', 'controller-0 type is incorrect'


def test_dc_config_controller_1():
    """
    Tests the dc config controller-1 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('controller-1')
    assert node.get_ip() == '10.2.3.127', 'controller-1 ip is incorrect'
    assert node.get_name() == 'controller-1', 'controller-1 name is incorrect'
    assert node.get_type() == 'Controller', 'controller-1 type is incorrect'


def test_dc_config_compute_0():
    """
    Tests the dc config compute-0 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('compute-0')
    assert node.get_ip() == '10.2.3.128', 'compute-0 ip is incorrect'
    assert node.get_name() == 'compute-0', 'compute-0 name is incorrect'
    assert node.get_type() == 'Compute', 'compute-0 type is incorrect'


def test_dc_config_compute_1():
    """
    Tests the dc config compute-1 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    node = configuration_manager.get_lab_config().get_node('compute-1')
    assert node.get_ip() == '10.2.3.129', 'compute-1 ip is incorrect'
    assert node.get_name() == 'compute-1', 'compute-1 name is incorrect'
    assert node.get_type() == 'Compute', 'compute-1 type is incorrect'


def test_dc_config_ipv4():
    """
    Tests the dc config is loaded as ipv4
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    assert configuration_manager.get_lab_config().is_ipv6() is False, 'lab is not ipv4'


def test_dc_subclouds_loaded():
    """
    Tests that the dc subclouds are loaded correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subclouds = configuration_manager.get_lab_config().get_subclouds()
    assert len(list(filter(lambda subcloud: subcloud.get_lab_name() == 'Subcloud1', subclouds))) == 1, 'Subcloud1 not in nodes'
    assert len(list(filter(lambda subcloud: subcloud.get_lab_name() == 'Subcloud2', subclouds))) == 1, 'Subcloud2 not in nodes'


def test_dc_subcloud1_config_loads_floating_ip():
    """
    Tests that the dc sublcloud1 config floating ip is loaded
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    assert subcloud1.get_floating_ip() == '10.2.3.130', 'floating ip was incorrect'


def test_dc_subcloud1_config_loads_lab_name():
    """
    Tests that the dc subcloud1 config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    assert subcloud1.get_lab_name() == 'Subcloud1', 'Sublcloud name was incorrect'


def test_dc_subcloud1_config_loads_lab_type():
    """
    Tests that the dc subcloud1 config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    assert subcloud1.get_lab_type() == 'Standard', 'subcloud type was incorrect'


def test_dc_subcloud1_config_loads_admin_credentials():
    """
    Tests the dc subcloud1 config admin credentials load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    admin_credentials = subcloud1.get_admin_credentials()
    assert admin_credentials is not None, 'error loading admin credentials'
    assert admin_credentials.get_user_name() == 'fake_user', 'User name is incorrect'
    assert admin_credentials.get_password() == 'fake_password', 'Password is incorrect'


def test_dc_subcloud1_config_loads_nodes():
    """
    Tests the dc subcloud1 config nodes load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    nodes = subcloud1.get_nodes()
    assert len(list(filter(lambda node: node.get_name() == 'controller-0', nodes))) == 1, 'Controller-0 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'controller-1', nodes))) == 1, 'Controller-1 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'compute-0', nodes))) == 1, 'Compute-0 not in nodes'
    assert len(list(filter(lambda node: node.get_name() == 'compute-1', nodes))) == 1, 'Compute-1 not in nodes'


def test_dc_subcloud1_config_controller_0():
    """
    Tests the dc subcloud1 config controller-0 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    node = subcloud1.get_node('controller-0')
    assert node.get_ip() == '10.2.3.131', 'Controller-0 ip is incorrect'
    assert node.get_name() == 'controller-0', 'Controller-0 name is incorrect'
    assert node.get_type() == 'Controller', 'Controller-0 type is incorrect'


def test_dc_subcloud1_config_controller_1():
    """
    Tests the dc subcloud1 config controller-1 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    node = subcloud1.get_node('controller-1')
    assert node.get_ip() == '10.2.3.132', 'Controller-1 ip is incorrect'
    assert node.get_name() == 'controller-1', 'Controller-1 name is incorrect'
    assert node.get_type() == 'Controller', 'Controller-1 type is incorrect'


def test_dc_subcloud1_config_compute_0():
    """
    Tests the dc subcloud1 config compute-0 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    node = subcloud1.get_node('compute-0')
    assert node.get_ip() == '10.2.3.133', 'Compute-0 ip is incorrect'
    assert node.get_name() == 'compute-0', 'Compute-0 name is incorrect'
    assert node.get_type() == 'Compute', 'Compute-0 type is incorrect'


def test_dc_subcloud1_config_compute_1():
    """
    Tests the dc subcloud1 config compute-1 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')
    node = subcloud1.get_node('compute-1')
    assert node.get_ip() == '10.2.3.134', 'Compute-1 ip is incorrect'
    assert node.get_name() == 'compute-1', 'Compute-1 name is incorrect'
    assert node.get_type() == 'Compute', 'Compute-1 type is incorrect'


def test_dc_subcloud1_config_ipv4():
    """
    Tests the dc subcloud1 config is loaded as ipv4
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud1 = configuration_manager.get_lab_config().get_subcloud('Subcloud1')

    assert subcloud1.is_ipv6() is False, 'lab is not ipv4'


def test_dc_subcloud2_config_loads_floating_ip():
    """
    Tests that the dc sublcloud2 config floating ip is loaded
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud2 = configuration_manager.get_lab_config().get_subcloud('Subcloud2')
    assert subcloud2.get_floating_ip() == '10.2.3.135', 'floating ip was incorrect'


def test_dc_subcloud2_config_loads_lab_name():
    """
    Tests that the dc subcloud2 config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud2 = configuration_manager.get_lab_config().get_subcloud('Subcloud2')
    assert subcloud2.get_lab_name() == 'Subcloud2', 'Sublcloud name was incorrect'


def test_dc_subcloud2_config_loads_lab_type():
    """
    Tests that the dc subcloud1 config lab name loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud2 = configuration_manager.get_lab_config().get_subcloud('Subcloud2')
    assert subcloud2.get_lab_type() == 'Simplex', 'subcloud type was incorrect'


def test_dc_subcloud2_config_loads_admin_credentials():
    """
    Tests the dc subcloud2 config admin credentials load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud2 = configuration_manager.get_lab_config().get_subcloud('Subcloud2')
    admin_credentials = subcloud2.get_admin_credentials()
    assert admin_credentials is not None, 'error loading admin credentials'
    assert admin_credentials.get_user_name() == 'fake_user', 'User name is incorrect'
    assert admin_credentials.get_password() == 'fake_password', 'Password is incorrect'


def test_dc_subcloud2_config_loads_nodes():
    """
    Tests the dc subcloud2 config nodes load correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud2 = configuration_manager.get_lab_config().get_subcloud('Subcloud2')
    nodes = subcloud2.get_nodes()
    assert len(list(filter(lambda node: node.get_name() == 'controller-0', nodes))) == 1, 'Controller-0 not in nodes'


def test_dc_subcloud2_config_controller_0():
    """
    Tests the dc subcloud2 config controller-0 node loads correctly
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud2 = configuration_manager.get_lab_config().get_subcloud('Subcloud2')
    node = subcloud2.get_node('controller-0')
    assert node.get_ip() == '10.2.3.136', 'Controller-0 ip is incorrect'
    assert node.get_name() == 'controller-0', 'Controller-0 name is incorrect'
    assert node.get_type() == 'Controller', 'Controller-0 type is incorrect'


def test_dc_subcloud2_config_ipv4():
    """
    Tests the dc subcloud2 config is loaded as ipv4
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)
    subcloud2 = configuration_manager.get_lab_config().get_subcloud('Subcloud2')

    assert subcloud2.is_ipv6() is False, 'lab is not ipv4'


def test_dc_is_dc_true():
    """
    Tests that is dc is true when we have subclouds
    Returns:

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    config_file_locations.set_lab_config_file(get_stx_resource_path('config/lab/files/template_dc.json5'))
    configuration_manager.load_configs(config_file_locations)

    assert configuration_manager.get_lab_config().is_dc(), 'Lab was not marked as dc'
