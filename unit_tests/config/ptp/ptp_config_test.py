from config.configuration_file_locations_manager import (
    ConfigurationFileLocationsManager,
)
from config.configuration_manager import ConfigurationManagerClass


def test_default_ptp_config():
    """
    Tests that the default ptp configuration is as expected.

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    default_config = configuration_manager.get_ptp_config()

    assert default_config is not None, "Default PTP config wasn't loaded successfully"
    assert len(default_config.get_all_hosts()) == 2, "There are two hosts in the PTP config"

    config_for_controller_0 = default_config.get_host("controller_0")
    assert len(config_for_controller_0.get_all_nics()) == 2, "There are two NIC assigned to controller-0 in the PTP config"

    first_nic = config_for_controller_0.get_nic("nic1")
    assert first_nic.get_sma1_to_nic2() == "output"
    assert first_nic.get_conn_to_ctrl1_nic1() == "enp81s0f1"
