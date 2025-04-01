import os

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords


def sanity_pre_requisite():
    """
    Sanity pre-requisite for the test case
    """
    # Sync the lab configuration between active and standby controller
    lab_config = ConfigurationManager.get_lab_config()
    active_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    user = lab_config.get_admin_credentials().get_user_name()

    # get the standby controller
    standby_controller = SystemHostListKeywords(active_controller_ssh).get_standby_controller()
    if not standby_controller:
        raise Exception("System does not have a standby controller")
    standby_host_name = standby_controller.get_host_name()
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    file_kw = FileKeywords(active_controller_ssh)
    # sync all subclouds files
    for sc_assets in deployment_assets_config.subclouds_deployment_assets.values():
        # get base path of the file
        for file in [sc_assets.get_deployment_config_file(), sc_assets.get_install_file(), sc_assets.get_bootstrap_file()]:
            # get the base path of the file
            base_file_path = os.path.join(os.path.dirname(file), "")
            # prepare remote path
            remote_path = f"{user}@{standby_host_name}:{base_file_path}"
            file_kw.execute_rsync(file, remote_path)


def subcloud_add(subcloud_name: str):
    """Add a subcloud to the system.

    Args:
        subcloud_name (str): name of the subcloud to be added
    """
    # Gets the SSH connection to the active controller of the central cloud.
    change_state_timeout = 60

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_add_kw = DcManagerSubcloudAddKeywords(ssh_connection)
    dcm_sc_add_kw.dcmanager_subcloud_add(subcloud_name)
    dcmanager_subcloud_manage_keywords = DcManagerSubcloudManagerKeywords(ssh_connection)
    dcmanager_subcloud_manage_output = dcmanager_subcloud_manage_keywords.get_dcmanager_subcloud_manage(subcloud_name, change_state_timeout)
    manage_status = dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management()
    get_logger().log_info(f"The management state of the subcloud {subcloud_name} {manage_status}")


@mark.p0
@mark.lab_has_min_2_subclouds
def test_dc_subcloud_add_simplex():
    """Verify subcloud Add works as expected

    Test Steps:
        - log onto system controller
        - add The subcloud
        - validate that the subcloud is added
    """
    sanity_pre_requisite()
    # read the config file for subcloud
    subcloud_name = "subcloud1"
    subcloud_add(subcloud_name)


@mark.p0
@mark.lab_has_subcloud
def test_dc_swact():
    """Test swact Host

    Test Steps:
    - Swact the host.
    - Verify that the host is changed.
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Swact the host
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list_keywords.get_active_controller()
    standby_controller = system_host_list_keywords.get_standby_controller()
    get_logger().log_info(f"A 'swact' operation is about to be executed in {ssh_connection}. Current controllers' configuration before this operation: Active controller = {active_controller.get_host_name()}, Standby controller = {standby_controller.get_host_name()}.")
    system_host_swact_keywords = SystemHostSwactKeywords(ssh_connection)
    system_host_swact_keywords.host_swact()

    # Gets the controllers after the execution of the swact operation.
    active_controller_after_swact = system_host_list_keywords.get_active_controller()
    standby_controller_after_swact = system_host_list_keywords.get_standby_controller()

    validate_equals(active_controller.get_id(), standby_controller_after_swact.get_id(), "Validate that active controller is now standby")
    validate_equals(standby_controller.get_id(), active_controller_after_swact.get_id(), "Validate that standby controller is now active")


@mark.p0
@mark.lab_has_min_2_subclouds
def test_dc_subcloud_add_duplex():
    """Verify subcloud Add works as expected

    Test Steps:
        - log onto system controller
        - add The subcloud
        - validate that the subcloud is added
    """
    sanity_pre_requisite()
    # read the config file for subcloud
    subcloud_name = "subcloud2"
    subcloud_add(subcloud_name)
