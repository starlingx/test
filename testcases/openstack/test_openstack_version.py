from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManagerClass
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


def test_openstack_version():
    """
    Test to retrieve openstack version present on lab

    Test Steps:
        - connect to active controller
        - run system cmd - cat /opt/platform/fluxcd/*/stx-openstack/*/metadata.yaml
        - retrieve the openstack version and log the important values like name, version & build date

    """
    configuration_manager = ConfigurationManagerClass()
    config_file_locations = ConfigurationFileLocationsManager()
    configuration_manager.load_configs(config_file_locations)
    cmd = configuration_manager.get_openstack_config().get_version_cmd()

    get_logger().log_info("Display App Version Step")
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    cmd_out = ssh_connection.send(cmd)

    if cmd_out:
        get_logger().log_info(f"App Name: {cmd_out[0]}")
        get_logger().log_info(f"App Version: {cmd_out[1]}")
        get_logger().log_info(f"App Build Date: {cmd_out[-1]}")
