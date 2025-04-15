from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p2
@mark.lab_has_subcloud
@mark.lab_has_secondary_system_controller
def test_rehome_one_subcloud(request):
    """
    Execute a subcloud rehome

    Test Steps:
        - Ensure both initial and target system controllers have the same date.
        - Unmanage the subcloud to be rehomed.
        - Shutdown both initial controller and subcloud
        - run dcmanager subcloud migration command.

    """

    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()

    origin_system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    destination_system_controller_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(origin_system_controller_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()

    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    subcloud_install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()

    get_logger().log_info(f"Running rehome command on {destination_system_controller_ssh}")
    DcManagerSubcloudAddKeywords(destination_system_controller_ssh).dcmanager_subcloud_add_migrate(subcloud_name, bootstrap_values=subcloud_bootstrap_values, install_values=subcloud_install_values)
    DcManagerSubcloudListKeywords(destination_system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="rehoming")
    DcManagerSubcloudListKeywords(destination_system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="complete")

    get_logger().log_info(f"Deleting subcloud from {origin_system_controller_ssh}")
    DcManagerSubcloudManagerKeywords(origin_system_controller_ssh).get_dcmanager_subcloud_unmanage(subcloud_name=subcloud_name, timeout=30)
    DcManagerSubcloudDeleteKeywords(origin_system_controller_ssh).dcmanager_subcloud_delete(subcloud_name=subcloud_name)

    get_logger().log_info(f"Running rehome command on {origin_system_controller_ssh}")
    DcManagerSubcloudAddKeywords(origin_system_controller_ssh).dcmanager_subcloud_add_migrate(subcloud_name, bootstrap_values=subcloud_bootstrap_values, install_values=subcloud_install_values)
    dcmanager_subcloud_list_keywords.validate_subcloud_status(subcloud_name=subcloud_name, status="rehoming")
    dcmanager_subcloud_list_keywords.validate_subcloud_status(subcloud_name=subcloud_name, status="complete")

    get_logger().log_info(f"Deleting subcloud from {destination_system_controller_ssh}")
    DcManagerSubcloudDeleteKeywords(destination_system_controller_ssh).dcmanager_subcloud_delete(subcloud_name=subcloud_name)
