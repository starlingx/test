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
def test_enroll_one_subcloud(request):
    """
    Execute a subcloud enroll

    Test Steps:
        - Ensure both initial and target system controllers have the same date.
        - Unmanage the subcloud to be rehomed.
        - Shutdown both initial controller and subcloud
        - run dcmanager subcloud migration command.

    """

    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    dcm_sc_list_kw = DcManagerSubcloudListKeywords(system_controller_ssh)
    subcloud_name = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_undeployed_subcloud_name()

    if subcloud_name is None:
        get_logger().log_info("No Undeployed Subcloud found deleting existing one")
        # Gets the lowest subcloud (the subcloud with the lowest id).
        get_logger().log_info("Obtaining subcloud with the lowest ID.")
        lowest_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
        get_logger().log_info(f"Subcloud with the lowest ID obtained: ID={lowest_subcloud.get_id()}, Name={lowest_subcloud.get_name()}, Management state={lowest_subcloud.get_management()}")
        subcloud_name = lowest_subcloud.get_name()
        dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(system_controller_ssh)
        # poweroff the subcloud.
        get_logger().log_test_case_step(f"Poweroff subcloud={subcloud_name}.")
        dcm_sc_manager_kw.set_subcloud_poweroff(subcloud_name)
        # delete the subcloud.
        dcm_sc_del_kw = DcManagerSubcloudDeleteKeywords(system_controller_ssh)
        dcm_sc_del_kw.dcmanager_subcloud_delete(subcloud_name)

    bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
    deployment_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add_enroll(subcloud_name=subcloud_name, bootstrap_values=bootstrap_values, install_values=install_values, deploy_config_file=deployment_config_file)
    DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_status(subcloud_name=subcloud_name, status="enroll-complete")
