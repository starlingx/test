"""Single subcloud deployment tests."""

import time

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_lifecycle_keywords import DcManagerSubcloudLifecycleKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords, pick_subcloud_with_fallback
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sync_files.sync_deployment_assets import SyncDeploymentAssets
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass


# --- Setup Helpers ---


def get_undeployed_subcloud_name() -> str:
    """Get an undeployed subcloud name, checking both system controllers.

    Uses SubcloudPickerKeywords.pick_undeployed_with_fallback to find a config
    subcloud not deployed on either system controller. If all are deployed, picks
    one via pick_subcloud_with_fallback and removes it.

    Returns:
        str: Subcloud name ready for deployment.
    """
    subcloud_name = SubcloudPickerKeywords.pick_undeployed_with_fallback()
    if subcloud_name is not None:
        return subcloud_name

    get_logger().log_info("All config subclouds are deployed, removing one to free it")
    owner_ssh, result = pick_subcloud_with_fallback(present_in_config=True)
    subcloud_name = result.get_name()
    DcManagerSubcloudLifecycleKeywords(owner_ssh).delete_subcloud(subcloud_name)
    return subcloud_name


def deploy_subcloud(ssh_connection: SSHConnection, subcloud_name: str, release_id: str = None) -> None:
    """Deploy a subcloud using dcmanager subcloud add and wait for completion.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Subcloud to deploy.
        release_id (str): Optional release ID for N-1/N-2 deployments.
    """
    get_logger().log_test_case_step(f"Deploy subcloud '{subcloud_name}'")
    start_time = time.time()
    DcManagerSubcloudAddKeywords(ssh_connection).dcmanager_subcloud_add(subcloud_name, release_id=release_id)
    elapsed = time.time() - start_time
    get_logger().log_info(f"Subcloud '{subcloud_name}' deploy completed in {elapsed:.1f} seconds")


def manage_subcloud(ssh_connection: SSHConnection, subcloud_name: str) -> None:
    """Wait for subcloud to come online and manage it.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Subcloud to manage.
    """
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Wait for subcloud '{subcloud_name}' to come online")
    dcm_sc_list_kw.validate_subcloud_availability_status(subcloud_name)

    get_logger().log_test_case_step(f"Manage subcloud '{subcloud_name}'")
    start_time = time.time()
    DcManagerSubcloudManagerKeywords(ssh_connection).get_dcmanager_subcloud_manage(subcloud_name, timeout=60)
    elapsed = time.time() - start_time
    get_logger().log_info(f"Subcloud '{subcloud_name}' managed in {elapsed:.1f} seconds")



# --- Simplex Test Cases ---


@mark.p0
@mark.subcloud_lab_is_simplex
def test_deploy_single_simplex_subcloud_n_release():
    """Deploy a single simplex subcloud on N release and validate health.

    Preconditions:
        - System controller is accessible
        - At least one simplex subcloud is defined in the lab config

    Setup:
        - Sync deployment assets to standby controller
        - Find or free an undeployed subcloud

    Test Steps:
        1. Deploy subcloud using dcmanager subcloud add
        2. Wait for subcloud to come online
        3. Manage subcloud
        4. Validate subcloud sync is in-sync
        5. Validate subcloud cluster health

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    subcloud_name = get_undeployed_subcloud_name()

    deploy_subcloud(ssh_connection, subcloud_name)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' sync status is in-sync")
    DcManagerSubcloudListKeywords(ssh_connection).validate_subcloud_sync_status(subcloud_name, "in-sync")

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.subcloud_lab_is_simplex
def test_deploy_single_simplex_subcloud_n_minus_1_release():
    """Deploy a single simplex subcloud on N-1 release and validate health.

    Preconditions:
        - System controller is accessible
        - At least one simplex subcloud is defined in the lab config

    Setup:
        - Sync deployment assets to standby controller
        - Find or free an undeployed subcloud

    Test Steps:
        1. Deploy subcloud using dcmanager subcloud add with --release N-1
        2. Wait for subcloud to come online
        3. Manage subcloud
        4. Validate subcloud cluster health

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    subcloud_name = get_undeployed_subcloud_name()

    deploy_subcloud(ssh_connection, subcloud_name, release_id=n_minus_1_release)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


# --- Duplex Test Cases ---


@mark.p0
@mark.subcloud_lab_is_duplex
def test_deploy_single_duplex_subcloud_n_release():
    """Deploy a single duplex subcloud on N release and validate health.

    Preconditions:
        - System controller is accessible
        - At least one duplex subcloud is defined in the lab config

    Setup:
        - Sync deployment assets to standby controller
        - Find or free an undeployed subcloud

    Test Steps:
        1. Deploy subcloud using dcmanager subcloud add
        2. Wait for subcloud to come online
        3. Manage subcloud
        4. Validate subcloud sync is in-sync
        5. Validate subcloud cluster health

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    subcloud_name = get_undeployed_subcloud_name()

    deploy_subcloud(ssh_connection, subcloud_name)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' sync status is in-sync")
    DcManagerSubcloudListKeywords(ssh_connection).validate_subcloud_sync_status(subcloud_name, "in-sync")

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.subcloud_lab_is_duplex
def test_deploy_single_duplex_subcloud_n_minus_1_release():
    """Deploy a single duplex subcloud on N-1 release and validate health.

    Preconditions:
        - System controller is accessible
        - At least one duplex subcloud is defined in the lab config

    Setup:
        - Sync deployment assets to standby controller
        - Find or free an undeployed subcloud

    Test Steps:
        1. Deploy subcloud using dcmanager subcloud add with --release N-1
        2. Wait for subcloud to come online
        3. Manage subcloud
        4. Validate subcloud cluster health

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    subcloud_name = get_undeployed_subcloud_name()

    deploy_subcloud(ssh_connection, subcloud_name, release_id=n_minus_1_release)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


# --- N-2 Release Test Cases ---


@mark.p0
@mark.subcloud_lab_is_simplex
def test_deploy_single_simplex_subcloud_n_minus_2_release():
    """Deploy a single simplex subcloud on N-2 release and validate health.

    Preconditions:
        - System controller is accessible
        - At least one simplex subcloud is defined in the lab config

    Setup:
        - Sync deployment assets to standby controller
        - Find or free an undeployed subcloud

    Test Steps:
        1. Deploy subcloud using dcmanager subcloud add with --release N-2
        2. Wait for subcloud to come online
        3. Manage subcloud
        4. Validate subcloud cluster health

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    n_minus_2_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    subcloud_name = get_undeployed_subcloud_name()

    deploy_subcloud(ssh_connection, subcloud_name, release_id=n_minus_2_release)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.subcloud_lab_is_duplex
def test_deploy_single_duplex_subcloud_n_minus_2_release():
    """Deploy a single duplex subcloud on N-2 release and validate health.

    Preconditions:
        - System controller is accessible
        - At least one duplex subcloud is defined in the lab config

    Setup:
        - Sync deployment assets to standby controller
        - Find or free an undeployed subcloud

    Test Steps:
        1. Deploy subcloud using dcmanager subcloud add with --release N-2
        2. Wait for subcloud to come online
        3. Manage subcloud
        4. Validate subcloud cluster health

    Teardown:
        - None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    n_minus_2_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    subcloud_name = get_undeployed_subcloud_name()

    deploy_subcloud(ssh_connection, subcloud_name, release_id=n_minus_2_release)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()
