import re

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_sw_deploy_strategy_keywords import SwManagerSwDeployStrategyKeywords
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_create_config import SwManagerSwDeployStrategyCreateConfig
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords


# --- Helper Functions ---


def extract_patch_version(filepath: str, sw_version: str) -> int:
    """Extract the numeric patch version from a filename.

    Given sw_version='26.03' and filepath='26.03.200-software-rr.patch',
    extracts 200.

    Args:
        filepath: Full path to the patch file.
        sw_version: The base SW_VERSION (e.g. '26.03').

    Returns:
        int: The numeric patch version, or 0 if not found.
    """
    match = re.search(rf'{re.escape(sw_version)}\.(\d+)', filepath)
    return int(match.group(1)) if match else 0


def get_sw_version(ssh_connection: SSHConnection) -> str:
    """Read SW_VERSION from /etc/build.info on the target system.

    Args:
        ssh_connection: SSH connection to the target host.

    Returns:
        str: The SW_VERSION value (e.g. '26.03').
    """
    build_info_output = ssh_connection.send("grep SW_VERSION /etc/build.info")
    for line in build_info_output:
        if "SW_VERSION" in line:
            return line.split("=")[1].strip().strip('"')
    return ""


def find_highest_undeployed_patch(ssh_connection: SSHConnection, sw_version: str) -> str:
    """Find the highest undeployed .patch file in /home/sysadmin/.

    Lists patch files matching the sw_version, filters out those already
    deployed, and returns the one with the highest numeric version.

    Args:
        ssh_connection: SSH connection to the system controller.
        sw_version: The base SW_VERSION (e.g. '26.03').

    Returns:
        str: Full path to the highest undeployed patch file.

    Raises:
        AssertionError: If no matching or undeployed patch files are found.
    """
    # Find .patch files matching the release prefix
    file_keywords = FileKeywords(ssh_connection)
    all_files = file_keywords.get_files_in_dir("/home/sysadmin/")
    patch_files = [f"/home/sysadmin/{f}" for f in all_files if sw_version in f and f.endswith(".patch")]
    validate_equals(len(patch_files) > 0, True, f"At least one .patch file matching '{sw_version}' must exist in /home/sysadmin/.")

    # Filter out patches that are already deployed
    deployed_releases = SoftwareListKeywords(ssh_connection).get_software_list().get_release_name_by_state("deployed")
    get_logger().log_info(f"Currently deployed releases: {deployed_releases}")

    undeployed_patches = []
    for pf in patch_files:
        already_deployed = False
        for deployed in deployed_releases:
            # Strip any product prefix to get just the version number
            version_part = deployed.split("-", 1)[-1] if "-" in deployed else deployed
            if version_part in pf:
                already_deployed = True
                break
        if not already_deployed:
            undeployed_patches.append(pf)

    validate_equals(len(undeployed_patches) > 0, True, "At least one undeployed .patch file must exist in /home/sysadmin/.")
    get_logger().log_info(f"Undeployed patch files: {undeployed_patches}")

    # Select the highest by numeric version
    return max(undeployed_patches, key=lambda f: extract_patch_version(f, sw_version))


def swman_sw_deploy_strategy_create_apply(release: str):
    """Create and apply a sw-manager sw-deploy strategy on the system controller.

    Args:
        release: The software release to deploy (e.g. '26.03.200').
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    swman_deploy_kw = SwManagerSwDeployStrategyKeywords(central_ssh)

    get_logger().log_test_case_step("Through the VIM orchestration deploy the patch in the system controller")
    config = SwManagerSwDeployStrategyCreateConfig(release=release, delete=True)
    create_success = swman_deploy_kw.get_sw_deploy_strategy_create(config)
    validate_equals(create_success, True, "sw-deploy strategy created successfully.")

    # Wait for strategy to be ready to apply
    strategy_ready = swman_deploy_kw.wait_for_state(["ready-to-apply", "build-failed"])
    validate_equals(strategy_ready, True, "Strategy reached ready-to-apply state.")

    # Show strategy details
    strategy_show = swman_deploy_kw.get_sw_deploy_strategy_show().get_swmanager_sw_deploy_strategy_show()
    get_logger().log_info(f"Created sw-deploy strategy: {strategy_show.get_strategy_uuid()} for release {strategy_show.get_release_id()}")

    # Apply the strategy
    get_logger().log_test_case_step("Apply the strategy")
    apply_success = swman_deploy_kw.get_sw_deploy_strategy_apply()
    validate_equals(apply_success, True, "sw-deploy strategy apply command succeeded.")

    # Wait for strategy to complete
    strategy_done = swman_deploy_kw.wait_for_state(["applied", "apply-failed"])
    validate_equals(strategy_done, True, "Strategy reached applied state.")

    # Verify completion
    strategy_show = swman_deploy_kw.get_sw_deploy_strategy_show().get_swmanager_sw_deploy_strategy_show()
    get_logger().log_info(f"Strategy state: {strategy_show.get_state()}, completion: {strategy_show.get_current_phase_completion()}")
    validate_equals(strategy_show.get_current_phase_completion(), "100%", "deploy strategy completed successfully.")


def fetch_sw_list(ssh_connection: SSHConnection, log_message: str) -> list:
    """Fetch and log the software list from a host.

    Args:
        ssh_connection: SSH connection to the target host.
        log_message: Message to log before fetching.

    Returns:
        list: List of software release objects.
    """
    get_logger().log_test_case_step(log_message)
    sw_list = SoftwareListKeywords(ssh_connection).get_software_list().get_software_lists()
    get_logger().log_info(f"Current software list: {[sw.get_release() for sw in sw_list]}")
    return sw_list

# --- Test Cases ---


@mark.p2
def test_upload_patch_to_system_controller(request):
    """
    Find the highest patch file in /home/sysadmin/ matching the lab release, upload and deploy.

    Assumes the .patch file(s) have already been placed in /home/sysadmin/ on
    the system controller.

    Test Steps:
        - Get the SW_VERSION from the system controller
        - List .patch files in /home/sysadmin/ matching the release prefix
        - Filter out already-deployed patches and select the highest
        - Upload it via 'software upload'
        - Verify the patch becomes available
        - Create and apply sw-deploy strategy on the system controller
        - Verify the patch is deployed on the system controller

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    usm_keywords = USMKeywords(central_ssh)

    # Get the SW_VERSION and find the highest undeployed patch
    sw_version = get_sw_version(central_ssh)
    validate_equals(len(sw_version) > 0, True, "SW_VERSION must be present in /etc/build.info.")
    get_logger().log_info(f"Lab SW_VERSION: {sw_version}")

    patch_file_path = find_highest_undeployed_patch(central_ssh, sw_version)
    get_logger().log_info(f"Highest undeployed patch file: {patch_file_path}")

    # Upload the patch to the system controller
    upload_patch_out = usm_keywords.upload_patch_file(patch_file_path)
    upload_patch_obj = upload_patch_out.get_software_uploaded()
    validate_not_equals(upload_patch_obj, None, f"Patch file {patch_file_path} uploaded successfully.")
    release = upload_patch_obj[0].get_release()
    get_logger().log_info(f"Uploaded patch file: {patch_file_path} with release ID: {release}")

    # Verify the patch is available on the system controller
    sw_list = SoftwareListKeywords(central_ssh).get_software_list()
    patch_state = sw_list.get_release_state_by_release_name(release)
    validate_equals(patch_state, "available", f"Patch {release} is available on system controller after upload.")

    # Deploy the patch on the system controller via sw-manager
    get_logger().log_info(f"Deploying patch {release} on system controller via sw-manager")
    swman_sw_deploy_strategy_create_apply(release=release)

    # Verify the patch is deployed on the system controller
    sw_list = SoftwareListKeywords(central_ssh).get_software_list()
    patch_state = sw_list.get_release_state_by_release_name(release)
    validate_equals(patch_state, "deployed", f"Patch {release} is deployed on system controller.")


@mark.p2
@mark.lab_has_subcloud
def test_patch_apply(request):
    """
    Verify patch application on enrolled subcloud.

    Test Steps:
        - Get the highest deployed release from the system controller
        - Prestage the subcloud for sw-deploy
        - Create the dcmanager sw-deploy strategy for the highest deployed release
        - Apply strategy to deploy the patch on the subcloud
        - Verify the strategy completed successfully

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Get the subcloud name from the lab config
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    # Wait for subcloud to be healthy before patching
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    get_logger().log_info(f"Waiting for {subcloud_name} to be healthy before patch apply")
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

    # Gets the subcloud sysadmin password needed for prestage.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    sw_release = SoftwareListKeywords(central_ssh).get_software_list().get_release_name_by_state("deployed")
    latest_deployed_release = max(sw_release)

    validate_equals(len(sw_release) > 1, True, "System controller must have at least two releases deployed.")

    # Attempt sw-deploy-strategy delete to prevent sw-deploy-strategy create failure.
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()

    # Prestage the subcloud with the latest software deployed in the controller
    get_logger().log_info(f"Prestage {subcloud_name} with {sw_release}.")
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name=subcloud_name, syspass=subcloud_password, for_sw_deploy=True)

    # Create software deploy strategy (--with-delete so strategy delete also cleans up subcloud)
    get_logger().log_info(f"Create sw-deploy strategy for {subcloud_name} with release {latest_deployed_release}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, release=latest_deployed_release, with_delete=True)

    # Apply the previously created strategy
    get_logger().log_info(f"Apply strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_apply(target=subcloud_name)

    strategy_status = DcmanagerStrategyStepKeywords(central_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()

    # Verify that the strategy was applied correctly
    validate_equals(strategy_status, "complete", f"Software deploy completed successfully for subcloud {subcloud_name}.")

    # Delete the strategy on the system controller (also runs deploy delete on subcloud via --with-delete)
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()


@mark.p2
@mark.lab_has_subcloud
def test_patch_remove(request):
    """
    Verify patch removal on enrolled simplex subcloud.

    To remove a patch, you deploy-start the PREVIOUS release on the subcloud,
    which transitions the highest deployed release into 'removing' state.

    Test Steps:
        - Get deployed releases, identify highest and previous
        - software deploy start <previous_release>
        - Lock/deploy-host/unlock controller-0 (if RR=True)
        - Activate, complete, deploy delete
        - Verify the patch was removed

    """
    # Get the subcloud name and SSH
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Wait for subcloud to be healthy before patching
    get_logger().log_info(f"Waiting for {subcloud_name} to be healthy before patch removal")
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

    # Get all deployed releases on the subcloud
    sw_releases = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("deployed")
    validate_equals(len(sw_releases) > 1, True, "Need at least two deployed releases to test removal.")

    # Sort to find highest (to remove) and previous (to deploy-start with)
    sorted_releases = sorted(sw_releases)
    latest_release = sorted_releases[-1]
    previous_release = sorted_releases[-2]
    get_logger().log_info(f"Will remove {latest_release} by deploying {previous_release} on {subcloud_name}")

    # Deploy start the previous release
    usm_keywords = USMKeywords(subcloud_ssh)
    usm_keywords.deploy_start(previous_release)

    # Wait for deploy-start-done
    usm_keywords.wait_for_deploy_state("deploy-start-done")

    # Get the RR flag from deploy show
    deploy_show_kw = SoftwareDeployShowKeywords(subcloud_ssh)
    deploy_show_obj = deploy_show_kw.get_software_deploy_show().get_software_deploy_show()
    rr = deploy_show_obj.get_rr().lower() == "true"
    get_logger().log_info(f"Removing release: {latest_release}, RR: {rr}")

    # Lock → deploy host → unlock (lock only if RR=True)
    lock_kw = SystemHostLockKeywords(subcloud_ssh)
    if rr:
        get_logger().log_info("Locking controller-0 (RR=True)")
        lock_kw.lock_host("controller-0")

    usm_keywords.software_deploy_host("controller-0")

    if rr:
        get_logger().log_info("Unlocking controller-0")
        lock_kw.unlock_host("controller-0")
        lock_kw.wait_for_host_unlocked("controller-0")

    # Wait for deploy-host-done, activate, complete, delete
    usm_keywords.wait_for_deploy_state("deploy-host-done")

    usm_keywords.software_deploy_activate()
    usm_keywords.wait_for_deploy_state("deploy-activate-done")

    usm_keywords.software_deploy_complete()
    usm_keywords.software_deploy_delete()

    # Verify the patch was removed
    sw_list_after = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("deployed")
    get_logger().log_info(f"Releases after removal: {sw_list_after}")
    validate_equals(latest_release not in sw_list_after, True, f"Patch {latest_release} was removed from subcloud.")
    get_logger().log_info(f"Patch {latest_release} successfully removed from {subcloud_name}")


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
