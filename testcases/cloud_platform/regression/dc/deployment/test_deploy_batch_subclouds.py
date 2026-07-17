"""Batch subcloud deployment tests."""

from typing import List

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_lifecycle_keywords import DcManagerSubcloudLifecycleKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import DEPLOY_IN_PROGRESS_STATES, DcManagerSubcloudStateWatcherKeywords
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sync_files.sync_deployment_assets import SyncDeploymentAssets
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass


# --- Setup Helpers ---


def ensure_all_subclouds_undeployed(primary_ssh: SSHConnection, secondary_ssh: SSHConnection, subcloud_names: List[str]) -> None:
    """Ensure all config subclouds are undeployed from both system controllers.

    For each subcloud that exists on either controller, it will be powered off,
    unmanaged, and deleted.

    Args:
        primary_ssh (SSHConnection): SSH connection to the primary system controller.
        secondary_ssh (SSHConnection): SSH connection to the secondary system controller, or None.
        subcloud_names (List[str]): List of subcloud names to ensure are undeployed.
    """
    for subcloud_name in subcloud_names:
        owner_ssh = SubcloudPickerKeywords.find_subcloud_owner(subcloud_name, primary_ssh, secondary_ssh)
        if owner_ssh is not None:
            get_logger().log_info(f"Subcloud '{subcloud_name}' is deployed, removing it")
            DcManagerSubcloudLifecycleKeywords(owner_ssh).delete_subcloud(subcloud_name)
        else:
            get_logger().log_info(f"Subcloud '{subcloud_name}' is not deployed on any system controller")


# --- Test Cases ---


@mark.p0
@mark.lab_has_subcloud
def test_deploy_subclouds_in_batch_n_release():
    """Deploy all config subclouds on N release and validate health.

    Deploys all subclouds defined in the lab config on the primary system
    controller. Existing subclouds are removed first regardless of which
    system controller owns them.

    Preconditions:
        - System controller is accessible
        - Subclouds are defined in the lab config

    Setup:
        - Sync deployment assets to standby controller
        - Remove all config subclouds from both system controllers

    Test Steps:
        1. Deploy all config subclouds using dcmanager subcloud add
        2. Wait for each subcloud to come online
        3. Manage each subcloud
        4. Validate sync status is in-sync for each subcloud
        5. Validate cluster health on each subcloud

    Teardown:
        - None
    """
    primary_ssh = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    secondary_config = lab_config.get_secondary_system_controller_config()
    secondary_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh() if secondary_config is not None else None

    config_subcloud_names = lab_config.get_subcloud_names()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(primary_ssh).sync_assets()

    get_logger().log_setup_step("Ensure all config subclouds are undeployed")
    ensure_all_subclouds_undeployed(primary_ssh, secondary_ssh, config_subcloud_names)

    # Deploy all subclouds (fire all without waiting)
    get_logger().log_test_case_step("Deploy all config subclouds")
    for subcloud_name in config_subcloud_names:
        get_logger().log_info(f"Triggering deploy for subcloud '{subcloud_name}'")
        DcManagerSubcloudAddKeywords(primary_ssh).dcmanager_subcloud_add(subcloud_name, wait_for_status=False)

    # Watch all subclouds reach deploy complete
    get_logger().log_test_case_step("Wait for all subclouds to reach deploy complete")
    DcManagerSubcloudStateWatcherKeywords(primary_ssh).watch_subclouds(
        subcloud_names=config_subcloud_names,
        field_to_watch="deploy_status",
        in_progress_states=DEPLOY_IN_PROGRESS_STATES,
        complete_state="complete",
    )

    dcm_sc_list_kw = DcManagerSubcloudListKeywords(primary_ssh)
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(primary_ssh)

    get_logger().log_test_case_step("Wait for all subclouds to come online and manage them")
    for subcloud_name in config_subcloud_names:
        get_logger().log_info(f"Waiting for subcloud '{subcloud_name}' to come online")
        dcm_sc_list_kw.validate_subcloud_availability_status(subcloud_name)

        get_logger().log_info(f"Managing subcloud '{subcloud_name}'")
        dcm_sc_manager_kw.get_dcmanager_subcloud_manage(subcloud_name, timeout=60)

    # Validate sync status for all subclouds
    get_logger().log_test_case_step("Validate sync status for all subclouds")
    for subcloud_name in config_subcloud_names:
        get_logger().log_info(f"Validating sync status for subcloud '{subcloud_name}'")
        dcm_sc_list_kw.validate_subcloud_sync_status(subcloud_name, "in-sync")

    # Validate health on each subcloud
    get_logger().log_test_case_step("Validate cluster health on all subclouds")
    for subcloud_name in config_subcloud_names:
        get_logger().log_info(f"Validating health on subcloud '{subcloud_name}'")
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.lab_has_subcloud
def test_deploy_subclouds_in_batch_n_minus_1_release():
    """Deploy all config subclouds on N-1 release and validate health.

    Deploys all subclouds defined in the lab config on the primary system
    controller using the N-1 release. Existing subclouds are removed first
    regardless of which system controller owns them.

    Preconditions:
        - System controller is accessible
        - Subclouds are defined in the lab config

    Setup:
        - Sync deployment assets to standby controller
        - Remove all config subclouds from both system controllers

    Test Steps:
        1. Deploy all config subclouds using dcmanager subcloud add with --release N-1
        2. Wait for each subcloud to come online
        3. Manage each subcloud
        4. Validate cluster health on each subcloud

    Teardown:
        - None
    """
    primary_ssh = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    secondary_config = lab_config.get_secondary_system_controller_config()
    secondary_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh() if secondary_config is not None else None

    config_subcloud_names = lab_config.get_subcloud_names()
    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(primary_ssh).sync_assets()

    get_logger().log_setup_step("Ensure all config subclouds are undeployed")
    ensure_all_subclouds_undeployed(primary_ssh, secondary_ssh, config_subcloud_names)

    # Deploy all subclouds with N-1 release (fire all without waiting)
    get_logger().log_test_case_step(f"Deploy all config subclouds with release {n_minus_1_release}")
    for subcloud_name in config_subcloud_names:
        get_logger().log_info(f"Triggering deploy for subcloud '{subcloud_name}' with release {n_minus_1_release}")
        DcManagerSubcloudAddKeywords(primary_ssh).dcmanager_subcloud_add(subcloud_name, release_id=n_minus_1_release, wait_for_status=False)

    # Watch all subclouds reach deploy complete
    get_logger().log_test_case_step("Wait for all subclouds to reach deploy complete")
    DcManagerSubcloudStateWatcherKeywords(primary_ssh).watch_subclouds(
        subcloud_names=config_subcloud_names,
        field_to_watch="deploy_status",
        in_progress_states=DEPLOY_IN_PROGRESS_STATES,
        complete_state="complete",
    )

    dcm_sc_list_kw = DcManagerSubcloudListKeywords(primary_ssh)
    dcm_sc_manager_kw = DcManagerSubcloudManagerKeywords(primary_ssh)

    get_logger().log_test_case_step("Wait for all subclouds to come online and manage them")
    for subcloud_name in config_subcloud_names:
        get_logger().log_info(f"Waiting for subcloud '{subcloud_name}' to come online")
        dcm_sc_list_kw.validate_subcloud_availability_status(subcloud_name)

        get_logger().log_info(f"Managing subcloud '{subcloud_name}'")
        dcm_sc_manager_kw.get_dcmanager_subcloud_manage(subcloud_name, timeout=60)

    # Validate health on each subcloud (no sync check for N-1)
    get_logger().log_test_case_step("Validate cluster health on all subclouds")
    for subcloud_name in config_subcloud_names:
        get_logger().log_info(f"Validating health on subcloud '{subcloud_name}'")
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        HealthKeywords(subcloud_ssh).validate_healty_cluster()
