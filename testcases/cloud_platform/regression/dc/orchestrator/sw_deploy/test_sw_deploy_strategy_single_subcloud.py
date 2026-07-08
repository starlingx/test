from pytest import fail, mark

from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_strategy_cleanup_keywords import DcmanagerStrategyCleanupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass


# --- Helper Functions ---


def cleanup_strategy(ssh_connection: SSHConnection) -> None:
    """Delete sw-deploy-strategy if it exists.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
    """
    get_logger().log_teardown_step("Delete sw-deploy-strategy")
    DcmanagerStrategyCleanupKeywords(ssh_connection).cleanup_strategy("sw-deploy")


def get_highest_release_for_load(ssh_connection: SSHConnection, load: str, state: str = "deployed") -> str:
    """Get the highest release version matching a load prefix from software list.

    For sw-deploy, we need the full release name (e.g. WRCP-26.03.200) not just
    the load identifier (26.03). This function finds the highest version matching
    the given load prefix in the specified state.

    Args:
        ssh_connection (SSHConnection): SSH connection to query software list.
        load (str): Load prefix to match (e.g. "26.03" or "25.09").
        state (str): Release state to filter by (e.g. "deployed", "unavailable").

    Returns:
        str: The highest release name matching the load (e.g. "WRCP-26.03.200").

    Raises:
        ValueError: If no release matches the load in the given state.
    """
    software_list = SoftwareListKeywords(ssh_connection).get_software_list()
    releases = software_list.get_release_name_by_state(state)
    matching = [r for r in releases if load in r]
    if not matching:
        fail(f"No release found matching load '{load}' in state '{state}'. Available: {releases}")
    return max(matching)


def run_sw_deploy_strategy(system_controller_ssh: SSHConnection, subcloud_name: str, release: str) -> None:
    """Create, apply, and verify sw-deploy-strategy for a subcloud.

    Args:
        system_controller_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud to target.
        release (str): Full release name to deploy (e.g. WRCP-26.03.200).
    """
    strategy_keywords = DcmanagerSwDeployStrategy(system_controller_ssh)

    get_logger().log_info(f"Creating sw-deploy-strategy for subcloud {subcloud_name} with release {release}")
    strategy_keywords.dcmanager_sw_deploy_strategy_create(
        subcloud_name=subcloud_name,
        release=release,
        with_delete=True,
    )

    get_logger().log_info("Applying sw-deploy-strategy")
    strategy_keywords.dcmanager_sw_deploy_strategy_apply(target=subcloud_name)

    # Verify strategy step completed
    strategy_status = DcmanagerStrategyStepKeywords(system_controller_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()
    validate_equals(strategy_status, "complete", f"Software deploy strategy step completed for subcloud {subcloud_name}")

    # Verify subcloud deploy status is complete
    subcloud = DcManagerSubcloudListKeywords(system_controller_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    validate_equals(subcloud.get_deploy_status(), "complete", f"Subcloud {subcloud_name} deploy status should be complete after sw-deploy")

    get_logger().log_info("Deleting sw-deploy-strategy")
    strategy_keywords.dcmanager_sw_deploy_strategy_delete()


# --- SW Deploy to N Release ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_sw_deploy_strategy_single_simplex_subcloud_n_release(request):
    """Verify sw-deploy-strategy targeting N release on a simplex subcloud.

    The target release is the highest deployed release matching N load from
    software list. The subcloud may be running N (minor upgrade) or N-1 (major
    upgrade) — behavior depends on the lab state at execution time.
    Subcloud must be out-of-sync (software_sync_status != in-sync).

    Test Steps:
        1. Get highest deployed N release from software list
        2. Create sw-deploy-strategy targeting the subcloud with that release
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")

    run_sw_deploy_strategy(system_controller_ssh, subcloud_name, release)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_sw_deploy_strategy_single_duplex_subcloud_n_release(request):
    """Verify sw-deploy-strategy targeting N release on a duplex subcloud.

    The target release is the highest deployed release matching N load from
    software list. The subcloud may be running N (minor upgrade) or N-1 (major
    upgrade) — behavior depends on the lab state at execution time.
    Subcloud must be out-of-sync (software_sync_status != in-sync).

    Test Steps:
        1. Get highest deployed N release from software list
        2. Create sw-deploy-strategy targeting the subcloud with that release
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")

    run_sw_deploy_strategy(system_controller_ssh, subcloud_name, release)


# --- SW Deploy to N-1 Release ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_sw_deploy_strategy_single_simplex_subcloud_n_minus_1_release(request):
    """Verify sw-deploy-strategy targeting N-1 release on a simplex subcloud.

    The target release is the highest unavailable release matching N-1 load
    from software list. Subcloud must be out-of-sync.

    Test Steps:
        1. Get highest unavailable N-1 release from software list
        2. Create sw-deploy-strategy targeting the subcloud with that release
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_minus_1_load = str(CloudPlatformVersionManagerClass().get_last_major_release())
    release = get_highest_release_for_load(system_controller_ssh, n_minus_1_load, state="unavailable")
    get_logger().log_info(f"Target N-1 release resolved to: {release}")

    run_sw_deploy_strategy(system_controller_ssh, subcloud_name, release)


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_duplex
def test_sw_deploy_strategy_single_duplex_subcloud_n_minus_1_release(request):
    """Verify sw-deploy-strategy targeting N-1 release on a duplex subcloud.

    The target release is the highest unavailable release matching N-1 load
    from software list. Subcloud must be out-of-sync.

    Test Steps:
        1. Get highest unavailable N-1 release from software list
        2. Create sw-deploy-strategy targeting the subcloud with that release
        3. Apply the strategy
        4. Validate strategy completes
        5. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=False,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_minus_1_load = str(CloudPlatformVersionManagerClass().get_last_major_release())
    release = get_highest_release_for_load(system_controller_ssh, n_minus_1_load, state="unavailable")
    get_logger().log_info(f"Target N-1 release resolved to: {release}")

    run_sw_deploy_strategy(system_controller_ssh, subcloud_name, release)


# --- SW Deploy No-Op (subcloud already in-sync) ---


@mark.p2
@mark.lab_has_subcloud
def test_sw_deploy_strategy_single_subcloud_n_release_already_in_sync(request):
    """Verify sw-deploy-strategy completes with no action when subcloud is already in-sync.

    This test ensures that running sw-deploy on a subcloud that is already
    in-sync does not break anything. The operation should complete successfully
    with no changes applied.

    Test Steps:
        1. Find an online, in-sync subcloud
        2. Get highest deployed N release from software list
        3. Create sw-deploy-strategy targeting the subcloud
        4. Apply the strategy
        5. Validate strategy completes (no-op)
        6. Delete the strategy

    Teardown:
        - Delete strategy if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        in_sync=True,
    )

    subcloud_name = result.get_name()
    request.addfinalizer(lambda: cleanup_strategy(system_controller_ssh))

    n_load = str(CloudPlatformVersionManagerClass().get_sw_version())
    release = get_highest_release_for_load(system_controller_ssh, n_load, state="deployed")
    get_logger().log_info(f"Target N release resolved to: {release}")
    get_logger().log_info(f"Subcloud {subcloud_name} is already in-sync — expecting no-op")

    run_sw_deploy_strategy(system_controller_ssh, subcloud_name, release)
