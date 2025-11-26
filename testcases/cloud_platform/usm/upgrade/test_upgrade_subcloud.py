from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass


def fetch_sw_list(ssh_connection: SSHConnection, log_message: str) -> list:
    """Fetches the software list from the given SSH connection and logs the information.

    Args:
        ssh_connection (SSHConnection): The SSH connection to the system controller or subcloud.
        log_message (str): Optional message to log before fetching the software list.

    Returns:
        list: A list of software releases.
    """
    get_logger().log_test_case_step(log_message)
    sw_list = SoftwareListKeywords(ssh_connection).get_software_list().get_software_lists()
    get_logger().log_info(f"Current software list: {[sw.get_release() for sw in sw_list]}")
    return sw_list


@mark.p2
@mark.lab_has_subcloud
def test_upgrade_n_1_subcloud():
    """
    Upgrade the N-1 release subcloud to N release and verify the upgrade was successful.

    Assumes that:
    - One Subcloud is added with release N-1.
    - The subcloud is online and reachable.
    """
    get_logger().log_info("Starting N-1 upgrade test for subcloud.")

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    cp_version_manager_obj = CloudPlatformVersionManagerClass()
    # latest release is the one we are currently running
    latest_release = cp_version_manager_obj.get_sw_version().get_name()
    # get n-1 release
    n_1_release = cp_version_manager_obj.get_last_major_release().get_name()
    # get the subcloud with the release
    subcloud_obj = dcm_sc_list_kw.get_one_subcloud_by_release(n_1_release)
    subcloud_name = subcloud_obj.get_name()
    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    msg = "Fetch software list before prestage-strategy "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")
    AlarmListKeywords(subcloud_ssh).wait_for_all_alarms_cleared()
    # dcmanager prestage-strategy create / apply / delete
    dcman_prestage_kw = DcmanagerPrestageStrategyKeywords(central_ssh)
    dcman_prestage_kw.dc_manager_prestage_strategy_create_apply_delete(sw_deploy=True, subcloud_name=subcloud_name)
    msg = "Fetch software list after dcmanager prestage-strategy on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")

    # find out the latest release version from the list of software releases
    # latest_release wil have the number part of the release e.g. 25.09
    # but we need full name as displayed in software list
    sw_list = SoftwareListKeywords(central_ssh).get_software_list().get_software_lists()
    full_sw_name = ""
    for sw in sw_list:
        if latest_release in sw.get_release():
            full_sw_name = sw.get_release()

    if not full_sw_name:
        get_logger().log_error(f"Release {latest_release} not found in the software list.")
        raise Exception(f"Release {latest_release} not found in the software list.")

    # dcmanager sw-deploy-strategy create / apply / delete
    dcman_sw_deploy_kw = DcmanagerSwDeployStrategy(central_ssh)
    dcman_sw_deploy_kw.dc_manager_sw_deploy_strategy_create_apply_delete(subcloud_name, full_sw_name)
    msg = "Fetch software list after dcmanager sw-deploy-strategy on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    sw_list = fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")
    # verify that the patch/release is applied on the subcloud
    for sw in sw_list:
        get_logger().log_info(f"Release: {sw.get_release()} is {sw.get_state()}")
        validate_equals(sw.get_state(), "deploying", "patch/release applied successfully.")
        # TO-DO: switch the line above assert for "complete" with software deploy show
