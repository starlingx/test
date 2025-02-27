from config.configuration_file_locations_manager import (
    ConfigurationFileLocationsManager,
)
from config.configuration_manager import ConfigurationManager
from framework.resources.resource_finder import get_stx_resource_path
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords


def test_generate_ptp_setup_from_template():
    """
    Tests that the generation of a PTPSetup from a Config and Template works as expected.

    """
    config_file_locations = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(config_file_locations)

    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_setup_template.json5")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)

    ptp4l_setup_list = ptp_setup.get_ptp4l_setup_list()
    assert len(ptp4l_setup_list) == 4
    phc2sys_setup_list = ptp_setup.get_phc2sys_setup_list()
    assert len(phc2sys_setup_list) == 4
    ts2phc_setup_list = ptp_setup.get_ts2phc_setup_list()
    assert len(ts2phc_setup_list) == 1

    clock_setup_list = ptp_setup.get_clock_setup_list()
    assert len(clock_setup_list) == 1
    clock1 = clock_setup_list[0]
    clock1_interfaces = clock1.get_ptp_interfaces()
    assert len(clock1_interfaces) == 2
