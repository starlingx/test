import time

from pytest import mark

from framework.ssh.ssh_connection import SSHConnection
from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_delete_keywords import DcManagerSubcloudDeleteKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass

def validate_subcloud_is_undeployed(ssh_connection: SSHConnection) -> str:
    """Validates if config subcloud is undeployed. Delete if it
    is not.

    Args:
        ssh_connection (SSHConnection): SSH connection object.

    Returns:
        str: subcloudname
    """
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)

    subcloud_list_obj = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects()
    subcloud_name_list = [sc.name for sc in subcloud_list_obj]
    config_subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    if config_subcloud_name in subcloud_name_list:
        get_logger().log_info("No Undeployed Subcloud found deleting existing one")
        dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
        # poweroff the subcloud.
        get_logger().log_test_case_step(f"Poweroff subcloud={config_subcloud_name}.")
        dcm_sc_manager_kw.set_subcloud_poweroff(config_subcloud_name)
        # Unmanage the subcloud.
        if dcm_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(config_subcloud_name).get_management() == "managed":
            get_logger().log_test_case_step(f"Unmanage subcloud={config_subcloud_name}.")
            dcm_sc_manage_output = dcm_sc_manager_kw.get_dcmanager_subcloud_unmanage(config_subcloud_name, timeout=10)
            get_logger().log_info(f"The management state of the subcloud {config_subcloud_name} was changed to {dcm_sc_manage_output.get_dcmanager_subcloud_manage_object().get_management()}.")

        # delete the subcloud.
        dcm_sc_del_kw = DcManagerSubcloudDeleteKeywords(ssh_connection)
        dcm_sc_del_kw.dcmanager_subcloud_delete(config_subcloud_name)

    return config_subcloud_name

def subcloud_addn_minus_release(subcloud_name: str, release_id: str):
    """Add a subcloud to the system, expecting out-of-sync status
    since it is an N-1 or N-2 release.

    Args:
        subcloud_name (str): name of the subcloud to be added
        release_id (str): release id of the subcloud
    """
    # Gets the SSH connection to the active controller of the central cloud.
    change_state_timeout = 60  # seconds

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_add_kw = DcManagerSubcloudAddKeywords(ssh_connection)
    dcm_sc_add_kw.dcmanager_subcloud_add(subcloud_name, release_id=release_id)
    # check for the subcloud online status before trigerring the manage command
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    dcm_sc_list_kw.validate_subcloud_availability_status(subcloud_name)
    dcmanager_subcloud_manage_keywords = DcManagerSubcloudManagerKeywords(ssh_connection)
    # Record the start time for to know the transition time
    start_time = time.time()
    # Wait for the subcloud to be in the managed state
    dcmanager_subcloud_manage_output = dcmanager_subcloud_manage_keywords.get_dcmanager_subcloud_manage(subcloud_name, change_state_timeout)
    # Check the elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time
    get_logger().log_info(f"Elapsed time for subcloud {subcloud_name} to be in managed state: {elapsed_time} seconds")
    manage_status = dcmanager_subcloud_manage_output.get_dcmanager_subcloud_manage_object().get_management()
    get_logger().log_info(f"The management state of the subcloud {subcloud_name} {manage_status}")

    DcManagerSubcloudListKeywords(ssh_connection).validate_subcloud_sync_status(subcloud_name, "out-of-sync")


@mark.p0
def test_dc_subcloud_add_n_1_simplex():
    """Verify subcloud Add works for N-1 as expected

    Test Steps:
        - log onto system controller
        - add The subcloud
        - validate that the subcloud is added
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    n_1_release = CloudPlatformVersionManagerClass().get_last_major_release()
    subcloud_name = validate_subcloud_is_undeployed(ssh_connection)
    subcloud_addn_minus_release(subcloud_name, release_id=str(n_1_release))

@mark.p0
def test_dc_subcloud_add_n_2_simplex():
    """Verify subcloud Add works for N-2 as expected

    Test Steps:
        - log onto system controller
        - add The subcloud
        - validate that the subcloud is added
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    n_2_release = CloudPlatformVersionManagerClass().get_second_last_major_release()
    subcloud_name = validate_subcloud_is_undeployed(ssh_connection)
    subcloud_addn_minus_release(subcloud_name, release_id=str(n_2_release))
