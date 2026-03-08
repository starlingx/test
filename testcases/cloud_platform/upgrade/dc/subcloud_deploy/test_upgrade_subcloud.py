from pytest import mark
import re

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_equals, validate_not_none
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords


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


def get_latest_and_n_minus_1_release(ssh_connection: SSHConnection) -> tuple[str, str]:
    """Determine latest (N) and N-1 releases from the lab using software list.

    The latest release (N) is identified as the one with state deployed.
    The N-1 release is identified as the other release (unavailable).

    Args:
        ssh_connection (SSHConnection): The SSH connection to the system.

    Returns:
        Both values returned are the numeric versions.
        tuple[str, str]: A tuple containing the latest release (N) and N-1 release.
    """
    sw_output = SoftwareListKeywords(ssh_connection).get_software_list()

    deployed_versions = sw_output.get_product_version_by_state("deployed")
    validate_not_equals(len(deployed_versions), 0, "No deployed release found in software list to determine latest release (N).")
    latest_release = deployed_versions[0]

    # prefer N-1 as unavailable release.
    n_minus_1_candidates = sw_output.get_product_version_by_state("unavailable")
    if not n_minus_1_candidates:
        # If there is no 'unavailable' entry, consider any non-deployed entry as N-1.
        all_versions = sw_output.get_product_version_by_state("available")
        n_minus_1_candidates = [v for v in all_versions if v != latest_release]

    validate_not_equals(len(n_minus_1_candidates), 0, "No N-1 release candidate found in software list.")

    n_minus_1_release = n_minus_1_candidates[0]
    return latest_release, n_minus_1_release


def test_subcloud_software_deploy_delete() -> None:
    """Performs software deploy delete on the subcloud and verifies the final states."""
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    
    # Get configuration from USM config
    usm_config = ConfigurationManager.get_usm_config()
    subcloud_name = usm_config.get_subcloud_name()
    
    # Use specific subcloud from config
    if subcloud_name != "None":
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        latest_release, n_minus_1_release = get_latest_and_n_minus_1_release(central_ssh)

        # software deploy delete to finish upgrade/patch
        usm_keywords = USMKeywords(subcloud_ssh)
        sw_deploy_delete_output = usm_keywords.software_deploy_delete(sudo=False)
        get_logger().log_info(f"'software deploy delete' output: {sw_deploy_delete_output}")

        # fetch software list again in the subcloud to verify the final states of the releases
        sw_list = fetch_sw_list(subcloud_ssh, f"Fetch software list after software deploy delete on subcloud ==> {subcloud_name}")

        for sw in sw_list:
            release_name = sw.get_release()
            state = sw.get_state()
            get_logger().log_info(f"Final state - Release: {release_name} is {state}")

            if latest_release in release_name:
                validate_equals(state, "deployed", "Latest release is deployed on subcloud after software deploy delete.")
            elif n_minus_1_release in release_name:
                validate_equals(state, "unavailable", "N-1 release is unavailable on subcloud after software deploy delete.")

def test_dcmanager_software_delete_only() -> None:
    """Creates a dcmanager strategy with --delete-only, for 1 subcloud or to a group of subclouds."""
    # get central cloud ssh
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)

    # get latest (N) and N-1 releases using software list
    latest_release, n_minus_1_release = get_latest_and_n_minus_1_release(central_ssh)

    # get the subcloud with the release and ssh
    subcloud_obj = dcm_sc_list_kw.get_one_subcloud_by_release(n_minus_1_release)
    subcloud_name_from_setup = subcloud_obj.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name_from_setup)
    
    # Get configuration from USM config
    usm_config = ConfigurationManager.get_usm_config()
    deploy_delete = usm_config.get_deploy_delete()
    subcloud_group = usm_config.get_subcloud_group()
    subcloud_name = usm_config.get_subcloud_name()

    if deploy_delete is True:    
        # Use subcloud from config if specified
        if subcloud_name != "None":
            subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

        # initial software list from subcloud before delete-only strategy
        initial_sw_list = fetch_sw_list(subcloud_ssh, f"Fetch initial software list from subcloud ==> {subcloud_name or subcloud_name_from_setup}")
        
        # dcmanager sw-deploy-strategy create / apply / delete
        dcman_sw_deploy_kw = DcmanagerSwDeployStrategy(central_ssh)
        dcman_sw_deploy_kw.dc_manager_sw_deploy_strategy_create_apply_delete(subcloud_name=subcloud_name, subcloud_group=subcloud_group, with_delete=False, delete_only=True)
        
        # software list from subcloud after delete-only strategy
        final_sw_list = fetch_sw_list(subcloud_ssh, f"Fetch final software list from subcloud after delete-only strategy ==> {subcloud_name or subcloud_name_from_setup}")
        
        # validate state changes
        for sw in final_sw_list:
            release_name = sw.get_release()
            state = sw.get_state()
            
            if latest_release in release_name:
                validate_equals(state, "deployed", f"Latest release {latest_release} should be deployed after delete-only strategy")
            elif n_minus_1_release in release_name:
                validate_list_contains(state, ["unavailable", "deployed"], f"N-1 release {n_minus_1_release} should be unavailable (upgrade) or deployed (patch) after delete-only strategy")
    else:
        get_logger().log_info("Not running software delete-only as deploy delete is disabled.")



@mark.p2
@mark.lab_has_subcloud
def test_prestage_subcloud():
    """
    Prestage the OSTree of N release from Central Cloud to 1 subcloud or to a group of subclouds.

    Assumes that:
    - The Subcloud is added with release N-1.
    - The Subcloud is online and reachable.
    
    Examples:
    - To prestage 1 subcloud:
    "subcloud_group": "None"
    "subcloud_name": "subcloud1"

    - To prestage a group of subclouds (all):
    "subcloud_group": "Default"
    "subcloud_name": "None"

    """
    # get central cloud ssh
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    
    # Get subcloud name from USM config
    usm_config = ConfigurationManager.get_usm_config()
    subcloud_group = usm_config.get_subcloud_group()
    subcloud_name = usm_config.get_subcloud_name()
    release = usm_config.get_to_release_ids()[0]
    
    # Extract version from release string
    validate_not_none(release, "Release is not valid.")
    match = re.search(r"(\d+)\.(\d+)", release)
    if match:
        major = match.group(1)
        minor = match.group(2).zfill(2)
        release_number = f"{major}.{minor}"
    
    # Use subcloud from config if specified
    if subcloud_name != "None":
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    
    msg = "Fetch software list before prestage-strategy "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    if subcloud_name != "None":
        fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")
        AlarmListKeywords(subcloud_ssh).wait_for_all_alarms_cleared()

    # dcmanager prestage-strategy create / apply / delete
    dcman_prestage_kw = DcmanagerPrestageStrategyKeywords(central_ssh)
    dcman_prestage_kw.dc_manager_prestage_strategy_create_apply_delete(release=release_number, sw_deploy=True, subcloud_group=subcloud_group, subcloud_name=subcloud_name)
    
    msg = "Fetch software list after dcmanager prestage-strategy on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    if subcloud_name != "None":
        fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")

@mark.p2
@mark.lab_has_subcloud
def test_upgrade_subcloud_from_central_cloud():
    """
    Upgrade 1 subcloud or a group of subclouds from release N-1 to N with dcmanager via Central Cloud until complete stage

    Assumes that:
    - The Subcloud was already prestaged.
    - The Subcloud has N-1 release deployed and N release available.
    - The Subcloud is online and reachable.
    - The Subcloud has the necessary precheck requirements from USM.
    """
    # get central cloud ssh
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    
    # Get subcloud name and group from USM config
    usm_config = ConfigurationManager.get_usm_config()
    subcloud_name = usm_config.get_subcloud_name()
    subcloud_group = usm_config.get_subcloud_group()
    snapshot = usm_config.get_snapshot()
    release = usm_config.get_to_release_ids()[0]
    
    # Get all subclouds for validation
    subcloud_objs = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects()
    subcloud_names = [subcloud_obj.get_name() for subcloud_obj in subcloud_objs]
    
    # dcmanager sw-deploy-strategy create / apply / delete
    dcman_sw_deploy_kw = DcmanagerSwDeployStrategy(central_ssh)
    dcman_sw_deploy_kw.dc_manager_sw_deploy_strategy_create_apply_delete(release=release, subcloud_group=subcloud_group, subcloud_name=subcloud_name, snapshot=snapshot)
    msg = "Fetch software list after dcmanager sw-deploy-strategy on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    
    # Validate all subclouds
    for sc_name in subcloud_names:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(sc_name)
        sw_list = fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {sc_name}")

        # verify latest release (N) on the subcloud is in state "deploying".
        for sw in sw_list:
            get_logger().log_info(f"Release: {sw.get_release()} is {sw.get_state()}")
            if release in sw.get_release():
                validate_equals(sw.get_state(),"deploying", f"Latest release is deploying on subcloud {sc_name}.")
                break

        # verify software deploy operation has completed successfully on the subcloud
        sw_deploy_show_obj = (SoftwareDeployShowKeywords(subcloud_ssh).get_software_deploy_show(sudo=False).get_software_deploy_show())
        from_release = sw_deploy_show_obj.get_from_release()
        to_release = sw_deploy_show_obj.get_to_release()
        deploy_state = sw_deploy_show_obj.get_state()
        get_logger().log_info(f"Software deploy show - From: {from_release}, To: {to_release}, State: {deploy_state}")
        validate_equals(deploy_state, "deploy-completed", f"Software deploy operation completed successfully on subcloud {sc_name}.")

@mark.p2
@mark.lab_has_subcloud
def test_rollback_subcloud_from_central_cloud():
    """
    Rollback 1 subcloud or a group of subclouds from release N to N-1 with dcmanager via Central Cloud

    Assumes that:
    - The Subcloud is in the complete stage.
    - There is no dcmanager orchestration in the Central Cloud.
    - The Subcloud is online and reachable.
    """

    # get central cloud ssh
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    
    # Get subcloud name and group from USM config
    usm_config = ConfigurationManager.get_usm_config()
    subcloud_name = usm_config.get_subcloud_name()
    subcloud_group = usm_config.get_subcloud_group()
    rollback = usm_config.get_rollback()
    release = usm_config.get_to_release_ids()[0] if usm_config.get_to_release_ids() else None
    
    # Validate rollback is true
    validate_equals(rollback, True, "Rollback must be true to execute this test.")
    
    # Get all subclouds for validation
    subcloud_objs = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects()
    subcloud_names = [subcloud_obj.get_name() for subcloud_obj in subcloud_objs]

    # dcmanager sw-deploy-strategy create / apply / delete
    dcman_sw_deploy_kw = DcmanagerSwDeployStrategy(central_ssh)
    dcman_sw_deploy_kw.dc_manager_sw_deploy_strategy_create_apply_delete(subcloud_group=subcloud_group, subcloud_name=subcloud_name, rollback=rollback)
    msg = "Fetch software list after dcmanager sw-deploy-strategy on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")

    # Validate all subclouds only if release was passed on get_to_release_ids
    if release:
        for sc_name in subcloud_names:
            subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(sc_name)
            sw_list = fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {sc_name}")

            # verify latest release (N) on the subcloud is in state "available".
            for sw in sw_list:
                get_logger().log_info(f"Release: {sw.get_release()} is {sw.get_state()}")
                if release in sw.get_release():
                    validate_equals(sw.get_state(),"available", f"Latest release is available on subcloud {sc_name}.")
                    break
