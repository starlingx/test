from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sync_files.sync_deployment_assets import SyncDeploymentAssets
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords


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


def subcloud_delete(subcloud_name: str):
    """Delete a subcloud from the system.

    Args:
        subcloud_name (str): name of the subcloud to be deleted
    """
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    sc_name = subcloud.get_name()
    msg = (f"Subcloud selected for deletion ID={subcloud.get_id()} ", f" Name={sc_name}, ", f" Management state={subcloud.get_management()} ")
    get_logger().log_info(msg)
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
    # poweroff the subcloud.
    get_logger().log_test_case_step(f"Poweroff subcloud={sc_name}.")
    dcm_sc_manager_kw.set_subcloud_poweroff(sc_name)
    # Unmanage the subcloud.
    if subcloud.get_management() == "managed":
        dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
        get_logger().log_test_case_step(f"Unmanage subcloud={sc_name}.")
        dcm_sc_manage_output = dcm_sc_manager_kw.get_dcmanager_subcloud_unmanage(sc_name, timeout=10)
        get_logger().log_info(f"The management state of the subcloud {sc_name} was changed to {dcm_sc_manage_output.get_dcmanager_subcloud_manage_object().get_management()}.")

    # delete the subcloud
    get_logger().log_test_case_step(f"Delete subcloud={sc_name}.")
    dcm_sc_del_kw = DcManagerSubcloudDeleteKeywords(ssh_connection)
    dcm_sc_del_kw.dcmanager_subcloud_delete(sc_name)

    # validate that the subcloud is deleted
    subclouds_list = dcm_sc_list_kw.get_dcmanager_subcloud_list()
    get_logger().log_test_case_step(f"Validate that subcloud={sc_name} is deleted.")
    validate_equals(subclouds_list.is_subcloud_in_output(sc_name), False, f"{sc_name} is no longer in the subcloud list.")


@mark.p0
@mark.subcloud_lab_is_simplex
def test_dc_subcloud_add_simplex():
    """Verify subcloud Add works as expected

    Test Steps:
        - log onto system controller
        - add The subcloud
        - validate that the subcloud is added
    """
    # fetch not deployed subcloud
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    SyncDeploymentAssets(ssh_connection).sync_assets()
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    subcloud_name = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_undeployed_subcloud_name("Simplex")
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
@mark.subcloud_lab_is_duplex
def test_dc_subcloud_add_duplex():
    """Verify subcloud Add works as expected

    Test Steps:
        - log onto system controller
        - add The subcloud
        - validate that the subcloud is added
    """
    # fetch not deployed subcloud
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    SyncDeploymentAssets(ssh_connection).sync_assets()
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    subcloud_name = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_undeployed_subcloud_name("Duplex")
    subcloud_add(subcloud_name)


@mark.p0
@mark.subcloud_lab_is_simplex
def test_dc_subcloud_delete_simplex():
    """
    Verify subcloud deletion works as expected

    Test Steps:
        - log onto system controller
        - list all subclouds and get the lowest id subcloud
        - unmanage the subcloud
        - power off the subcloud
        - delete the subcloud
        - validate that the subcloud is deleted
    """
    subcloud_name = "subcloud1"
    subcloud_delete(subcloud_name)


@mark.p0
@mark.subcloud_lab_is_duplex
def test_dc_subcloud_delete_duplex():
    """
    Verify subcloud deletion works as expected

    Test Steps:
        - log onto system controller
        - list all subclouds and get the lowest id subcloud
        - unmanage the subcloud
        - power off the subcloud
        - delete the subcloud
        - validate that the subcloud is deleted
    """
    subcloud_name = "subcloud2"
    subcloud_delete(subcloud_name)
