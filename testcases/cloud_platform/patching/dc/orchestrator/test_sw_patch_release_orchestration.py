from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_sw_deploy_strategy_keywords import SwManagerSwDeployStrategyKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords


@mark.p2
@mark.lab_has_subcloud
def test_patch_apply(request):
    """
    Verify patch application on subcloud

    Test Steps:
        - Prestage the subcloud with 25.09.1
        - Create the sw deploy strategy for 25.09.1
        - Apply strategy steps to subcloud

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_lower_id_async_subcloud()

    subcloud_name = lowest_subcloud.get_name()

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    sw_release = SoftwareListKeywords(central_ssh).get_software_list().get_release_name_by_state("deployed")
    latest_deployed_release = max(sw_release)

    if len(sw_release) <= 1:
        fail("Only one release in system controller, lab must have at least two releases deployed.")

    # Attempt sw-deploy-strategy delete to prevent sw-deploy-strategy create failure.
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()

    # Prestage the subcloud with the latest software deployed in the controller
    get_logger().log_info(f"Prestage {subcloud_name} with {sw_release}.")
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name=subcloud_name, syspass=subcloud_password, for_sw_deploy=True)

    # Create software deploy strategy
    get_logger().log_info(f"Create sw-deploy strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, sw_version=latest_deployed_release)

    # Apply the previously created strategy
    get_logger().log_info(f"Apply strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_apply(subcloud_name=subcloud_name)

    strategy_status = DcmanagerStrategyStepKeywords(central_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()

    # Verify that the strategy was applied correctly
    validate_equals(strategy_status, "complete", f"Software deploy completed successfully for subcloud {subcloud_name}.")


def swman_sw_deploy_strategy_create_apply(release: str):
    """Helper function to create and apply a software deploy strategy.

    Args:
        release (str): The software release to be used for the strategy.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    swman_deploy_kw = SwManagerSwDeployStrategyKeywords(central_ssh)

    get_logger().log_test_case_step("Through the VIM orchestration deploy the patch in the system controller")
    swman_obj = swman_deploy_kw.get_sw_deploy_strategy_create(release=release, delete=True)
    get_logger().log_info(f"Created sw-deploy strategy: {swman_obj.get_strategy_uuid()} for release {swman_obj.get_release_id()}")
    get_logger().log_info(f"release = {release}  get_release_id = {swman_obj.get_release_id()}")
    get_logger().log_test_case_step("Apply the strategy")
    swman_obj = swman_deploy_kw.get_sw_deploy_strategy_apply()
    # Verify that the strategy applied
    validate_equals(swman_obj.get_state(), "applied", "deploy strategy applied successfully.")

    # Verify that the current phase completed successfully
    validate_equals(swman_obj.get_current_phase_completion(), "100%", "deploy strategy completed successfully.")


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
def test_in_service_patch(request):
    """
    Verify insvc patch application on subcloud + rehomed

    Test Steps:
        - perform software list
        - Upload the IN-service patch in the system controller through command software upload
        - create and apply the sw-deploy strategy for the IN-service patch using below commands:
            - sw-manager sw-deploy-strategy create  --delete
            - sw-manager sw-deploy-strategy apply
        - perform software list on system controller
        - create and apply the dcmanager prestage strategy using below commands:
            - dcmanager prestage-strategy create --for-sw-deploy
            - dcmanager prestage-strategy apply
        -  perform software list on subcloud
        - delete the dcmanager prestage strategy using below command:
            - dcmanager prestage-strategy delete
        - create and apply the dcmanager sw-deploy strategy using below commands:
            - dcmanager sw-deploy-strategy create <subcloud_name> <release>
            - dcmanager sw-deploy-strategy apply <subcloud_name>
        - perform software list on subcloud
        - delete the dcmanager sw-deploy strategy using below command:
            - dcmanager sw-deploy-strategy delete
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcman_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcman_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()

    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    msg = "Fetch software list before patching on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")

    # Upload the IN-service patch in the system controller
    usm_keywords = USMKeywords(central_ssh)
    usm_config = ConfigurationManager.get_usm_config()
    patch_file_path = usm_config.get_patch_path()
    get_logger().log_info(f"Uploading IN-service patch file: {patch_file_path}")

    upload_patch_out = usm_keywords.upload_patch_file(patch_file_path)
    upload_patch_obj = upload_patch_out.get_software_uploaded()
    if not upload_patch_obj:
        raise Exception(f"Failed to upload patch file: {patch_file_path}")
    uploaded_file = upload_patch_obj[0].get_uploaded_file()
    release = upload_patch_obj[0].get_release()
    get_logger().log_info(f"Uploaded patch file: {uploaded_file} with release ID: {release}")

    # sw-manager sw-deploy-strategy create / apply / complete
    swman_sw_deploy_strategy_create_apply(release=release)
    msg = "Fetch software list after sw-deploy-strategy on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")

    # dcmanager prestage-strategy create / apply / delete
    dcman_prestage_kw = DcmanagerPrestageStrategyKeywords(central_ssh)
    dcman_prestage_kw.dc_manager_prestage_strategy_create_apply_delete(sw_deploy=True)
    msg = "Fetch software list after dcmanager prestage-strategy on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")

    # dcmanager sw-deploy-strategy create / apply / delete
    dcman_sw_deploy_kw = DcmanagerSwDeployStrategy(central_ssh)
    dcman_sw_deploy_kw.dc_manager_sw_deploy_strategy_create_apply_delete(subcloud_name, release)
    msg = "Fetch software list after dcmanager sw-deploy-strategy on "
    fetch_sw_list(central_ssh, f"{msg} Systemcontroller")
    sw_list = fetch_sw_list(subcloud_ssh, f"{msg} subcloud ==> {subcloud_name}")

    # verify that the patch is applied on subcloud
    for sw in sw_list:
        get_logger().log_info(f"Release: {sw.get_release()} is {sw.get_state()}")
        validate_equals(sw.get_state(), "deployed", "patch applied successfully.")
